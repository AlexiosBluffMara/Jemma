"""
Jemma Embed — Trimodal Gemma 4 Embedding Model

Converts Gemma 4 decoder-only models (E2B/E4B) into high-quality embedding
models supporting text, image, and audio in a unified vector space.

Architecture:
  1. Load Gemma 4 via AutoModelForMultimodalLM (preserves all encoders)
  2. Add QLoRA adapters for efficient training
  3. Extract last-hidden-state at EOS token position
  4. Project through optional linear head for Matryoshka dims
  5. L2-normalize to unit sphere

Supports:
  - Text-only embeddings (competitive with E5-Mistral, GTE-Qwen)
  - Image-text unified embeddings (competitive with CLIP, Jina-CLIP)
  - Audio-text unified embeddings (novel — no open-source competitor)
  - Trimodal: text + image + audio in one vector space
  - Matryoshka dimensions: truncate embeddings to any prefix length
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

log = logging.getLogger("jemma.embed")


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------
@dataclass
class EmbedConfig:
    """Configuration for the Jemma embedding model wrapper."""

    model_name: str = "unsloth/gemma-4-E2B-it"
    embed_dim: int = 2304
    matryoshka_dims: list[int] = field(default_factory=lambda: [256, 512, 1024, 2304])
    max_seq_length: int = 8192
    pooling: str = "last_token"        # last_token | mean | eos
    normalize: bool = True
    instruction_prefix: str = "Represent this for retrieval: "
    dtype: str = "bfloat16"
    quantization_bits: int = 4
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])


# ---------------------------------------------------------------------------
# Pooling strategies
# ---------------------------------------------------------------------------
def _pool_last_token(hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """Extract hidden state at the last non-padding token (EOS position)."""
    # Find last non-zero position in attention mask
    seq_lengths = attention_mask.sum(dim=1) - 1  # 0-indexed
    batch_size = hidden_states.shape[0]
    indices = seq_lengths.long().unsqueeze(-1).unsqueeze(-1)
    indices = indices.expand(-1, 1, hidden_states.shape[-1])
    pooled = hidden_states.gather(1, indices).squeeze(1)
    return pooled


def _pool_mean(hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """Mean pooling over non-padding tokens."""
    mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.shape).float()
    sum_embeddings = (hidden_states * mask_expanded).sum(dim=1)
    lengths = mask_expanded.sum(dim=1).clamp(min=1e-9)
    return sum_embeddings / lengths


def _pool_eos(hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """Pool at EOS token — same as last_token for Gemma (EOS is appended)."""
    return _pool_last_token(hidden_states, attention_mask)


POOLING_FNS = {
    "last_token": _pool_last_token,
    "mean": _pool_mean,
    "eos": _pool_eos,
}


# ---------------------------------------------------------------------------
# Matryoshka projection head
# ---------------------------------------------------------------------------
class MatryoshkaHead(nn.Module):
    """
    Optional learned linear projection that supports Matryoshka
    Representation Learning: embeddings can be truncated to any
    prefix dimension from matryoshka_dims and remain effective.

    During training, loss is computed at multiple truncation points.
    During inference, you just truncate the output vector.
    """

    def __init__(self, input_dim: int, matryoshka_dims: list[int]):
        super().__init__()
        self.input_dim = input_dim
        self.matryoshka_dims = sorted(matryoshka_dims)
        self.max_dim = max(matryoshka_dims)
        # Single linear projection to max dim (if different from input)
        if self.max_dim != input_dim:
            self.proj = nn.Linear(input_dim, self.max_dim, bias=False)
        else:
            self.proj = nn.Identity()

    def forward(self, x: Tensor) -> Tensor:
        return self.proj(x)

    def truncate(self, x: Tensor, dim: int) -> Tensor:
        """Truncate embedding to target dimension."""
        projected = self.forward(x)
        return projected[..., :dim]


# ---------------------------------------------------------------------------
# Main embedding model wrapper
# ---------------------------------------------------------------------------
class JemmaEmbedModel(nn.Module):
    """
    Wraps a Gemma 4 multimodal LM as an embedding model.

    Supports text, image, audio, and video inputs via the native
    Gemma 4 processor. Extracts final-layer hidden states and pools
    them into fixed-size embedding vectors.
    """

    def __init__(self, config: EmbedConfig):
        super().__init__()
        self.config = config
        self.pool_fn = POOLING_FNS[config.pooling]
        self.backbone = None
        self.processor = None
        self.matryoshka_head = MatryoshkaHead(
            config.embed_dim, config.matryoshka_dims
        )

    def load_backbone(self) -> None:
        """Load the Gemma 4 backbone with quantization + LoRA."""
        from transformers import AutoModelForMultimodalLM, AutoProcessor, BitsAndBytesConfig

        log.info(f"Loading backbone: {self.config.model_name}")

        dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16}
        dtype = dtype_map.get(self.config.dtype, torch.bfloat16)

        # Quantization config
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=self.config.quantization_bits == 4,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

        self.backbone = AutoModelForMultimodalLM.from_pretrained(
            self.config.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=dtype,
            trust_remote_code=True,
        )
        self.processor = AutoProcessor.from_pretrained(
            self.config.model_name,
            trust_remote_code=True,
        )
        log.info(f"Backbone loaded: {type(self.backbone).__name__}")

    def apply_lora(self) -> None:
        """Apply QLoRA adapters to the backbone for training."""
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

        self.backbone = prepare_model_for_kbit_training(self.backbone)

        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.lora_target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="FEATURE_EXTRACTION",
        )
        self.backbone = get_peft_model(self.backbone, lora_config)

        trainable, total = 0, 0
        for p in self.backbone.parameters():
            total += p.numel()
            if p.requires_grad:
                trainable += p.numel()
        log.info(
            f"LoRA applied: {trainable:,} trainable / {total:,} total "
            f"({100 * trainable / total:.2f}%)"
        )

    def _extract_hidden(
        self,
        input_ids: Tensor,
        attention_mask: Tensor,
        pixel_values: Optional[Tensor] = None,
        audio_values: Optional[Tensor] = None,
        **kwargs,
    ) -> Tensor:
        """Forward through backbone and extract last hidden states."""
        fwd_kwargs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "output_hidden_states": True,
            "return_dict": True,
        }
        if pixel_values is not None:
            fwd_kwargs["pixel_values"] = pixel_values
        if audio_values is not None:
            fwd_kwargs["audio_values"] = audio_values
        # Pass through any extra kwargs (token_type_ids, image_sizes, etc.)
        for k, v in kwargs.items():
            if k not in fwd_kwargs and v is not None:
                fwd_kwargs[k] = v

        with torch.amp.autocast("cuda", dtype=torch.bfloat16):
            outputs = self.backbone(**fwd_kwargs)

        # Last layer hidden states
        hidden = outputs.hidden_states[-1]
        return hidden

    def encode(
        self,
        input_ids: Tensor,
        attention_mask: Tensor,
        pixel_values: Optional[Tensor] = None,
        audio_values: Optional[Tensor] = None,
        truncate_dim: Optional[int] = None,
        **kwargs,
    ) -> Tensor:
        """
        Encode inputs to embedding vectors.

        Returns L2-normalized embeddings of shape (batch_size, embed_dim).
        If truncate_dim is set, returns truncated Matryoshka embeddings.
        """
        hidden = self._extract_hidden(
            input_ids, attention_mask,
            pixel_values=pixel_values,
            audio_values=audio_values,
            **kwargs,
        )
        pooled = self.pool_fn(hidden, attention_mask)

        if truncate_dim is not None:
            pooled = self.matryoshka_head.truncate(pooled, truncate_dim)
        else:
            pooled = self.matryoshka_head(pooled)

        if self.config.normalize:
            pooled = F.normalize(pooled, p=2, dim=-1)

        return pooled

    @torch.no_grad()
    def encode_text(
        self,
        texts: list[str],
        batch_size: int = 32,
        truncate_dim: Optional[int] = None,
        add_instruction: bool = True,
        show_progress: bool = False,
    ) -> Tensor:
        """Encode a list of text strings into embeddings."""
        self.eval()
        all_embeddings = []

        if add_instruction:
            texts = [self.config.instruction_prefix + t for t in texts]

        iterator = range(0, len(texts), batch_size)
        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="Encoding text")

        for start in iterator:
            batch_texts = texts[start : start + batch_size]
            encoded = self.processor(
                text=batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.config.max_seq_length,
            )
            encoded = {k: v.to(self.backbone.device) for k, v in encoded.items()}
            emb = self.encode(
                input_ids=encoded["input_ids"],
                attention_mask=encoded["attention_mask"],
                truncate_dim=truncate_dim,
            )
            all_embeddings.append(emb.cpu())

        return torch.cat(all_embeddings, dim=0)

    @torch.no_grad()
    def encode_image(
        self,
        images: list,
        texts: Optional[list[str]] = None,
        batch_size: int = 8,
        truncate_dim: Optional[int] = None,
    ) -> Tensor:
        """
        Encode images (PIL Images) into the same embedding space as text.
        Optionally pair with text for richer representations.
        """
        from PIL import Image
        self.eval()
        all_embeddings = []

        for start in range(0, len(images), batch_size):
            batch_images = images[start : start + batch_size]
            batch_texts = None
            if texts is not None:
                batch_texts = texts[start : start + batch_size]
            else:
                # Use a generic prompt so the model processes the image
                batch_texts = ["<start_of_image>Describe this image."] * len(batch_images)

            encoded = self.processor(
                text=batch_texts,
                images=batch_images,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.config.max_seq_length,
            )
            encoded = {k: v.to(self.backbone.device) for k, v in encoded.items()
                       if isinstance(v, Tensor)}
            emb = self.encode(
                input_ids=encoded.get("input_ids"),
                attention_mask=encoded.get("attention_mask"),
                pixel_values=encoded.get("pixel_values"),
                truncate_dim=truncate_dim,
            )
            all_embeddings.append(emb.cpu())

        return torch.cat(all_embeddings, dim=0)

    @torch.no_grad()
    def encode_audio(
        self,
        audio_arrays: list,
        texts: Optional[list[str]] = None,
        sample_rate: int = 16000,
        batch_size: int = 8,
        truncate_dim: Optional[int] = None,
    ) -> Tensor:
        """
        Encode audio (numpy arrays at 16kHz) into the same embedding space.
        Only supported on E2B/E4B (which have native audio encoders).
        """
        self.eval()
        all_embeddings = []

        for start in range(0, len(audio_arrays), batch_size):
            batch_audio = audio_arrays[start : start + batch_size]
            batch_texts = None
            if texts is not None:
                batch_texts = texts[start : start + batch_size]
            else:
                batch_texts = ["<start_of_audio>Describe this audio."] * len(batch_audio)

            encoded = self.processor(
                text=batch_texts,
                audios=batch_audio,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.config.max_seq_length,
            )
            encoded = {k: v.to(self.backbone.device) for k, v in encoded.items()
                       if isinstance(v, Tensor)}
            emb = self.encode(
                input_ids=encoded.get("input_ids"),
                attention_mask=encoded.get("attention_mask"),
                audio_values=encoded.get("audio_values"),
                truncate_dim=truncate_dim,
            )
            all_embeddings.append(emb.cpu())

        return torch.cat(all_embeddings, dim=0)


# ---------------------------------------------------------------------------
# Loss functions
# ---------------------------------------------------------------------------
class InfoNCELoss(nn.Module):
    """
    InfoNCE contrastive loss with in-batch negatives.
    Used for training the embedding model to pull together
    semantically similar pairs and push apart dissimilar ones.
    """

    def __init__(self, temperature: float = 0.02):
        super().__init__()
        self.temperature = temperature

    def forward(self, query_emb: Tensor, pos_emb: Tensor,
                neg_emb: Optional[Tensor] = None) -> Tensor:
        """
        Args:
            query_emb: (B, D) query/anchor embeddings
            pos_emb: (B, D) positive embeddings
            neg_emb: (B*N, D) optional hard negative embeddings
        Returns:
            Scalar loss
        """
        # In-batch negatives: all positives serve as negatives for other queries
        # Similarity matrix: (B, B) for in-batch + (B, B*N) for hard negatives
        sim_pos = torch.sum(query_emb * pos_emb, dim=-1) / self.temperature  # (B,)

        # All-pairs similarity for in-batch negatives
        sim_matrix = torch.mm(query_emb, pos_emb.t()) / self.temperature  # (B, B)

        if neg_emb is not None:
            sim_neg = torch.mm(query_emb, neg_emb.t()) / self.temperature  # (B, B*N)
            logits = torch.cat([sim_matrix, sim_neg], dim=1)  # (B, B + B*N)
        else:
            logits = sim_matrix

        # Labels: diagonal entries are the positives
        labels = torch.arange(query_emb.shape[0], device=query_emb.device)
        return F.cross_entropy(logits, labels)


class MatryoshkaLoss(nn.Module):
    """
    Matryoshka Representation Learning loss.
    Computes the contrastive loss at multiple embedding dimensions,
    weighted by importance (larger dims get lower weight since they
    subsume smaller dims).
    """

    def __init__(
        self,
        base_loss_fn: nn.Module,
        matryoshka_dims: list[int],
        dim_weights: Optional[list[float]] = None,
    ):
        super().__init__()
        self.base_loss_fn = base_loss_fn
        self.matryoshka_dims = sorted(matryoshka_dims)
        if dim_weights is None:
            # Decreasing importance: smaller dims matter more
            n = len(matryoshka_dims)
            self.dim_weights = [1.0 / (2 ** i) for i in range(n)]
        else:
            self.dim_weights = dim_weights
        # Normalize weights
        total = sum(self.dim_weights)
        self.dim_weights = [w / total for w in self.dim_weights]

    def forward(self, query_emb: Tensor, pos_emb: Tensor,
                neg_emb: Optional[Tensor] = None) -> Tensor:
        total_loss = torch.tensor(0.0, device=query_emb.device)

        for dim, weight in zip(self.matryoshka_dims, self.dim_weights):
            q_trunc = F.normalize(query_emb[..., :dim], p=2, dim=-1)
            p_trunc = F.normalize(pos_emb[..., :dim], p=2, dim=-1)
            n_trunc = None
            if neg_emb is not None:
                n_trunc = F.normalize(neg_emb[..., :dim], p=2, dim=-1)
            loss = self.base_loss_fn(q_trunc, p_trunc, n_trunc)
            total_loss = total_loss + weight * loss

        return total_loss


class CrossModalContrastiveLoss(nn.Module):
    """
    Cross-modal contrastive loss for aligning different modalities
    (text ↔ image, text ↔ audio) in a shared embedding space.

    Uses symmetric InfoNCE: loss_t2i + loss_i2t (CLIP-style).
    """

    def __init__(self, temperature: float = 0.02):
        super().__init__()
        self.temperature = temperature
        self.logit_scale = nn.Parameter(
            torch.tensor(math.log(1.0 / temperature))
        )

    def forward(self, emb_a: Tensor, emb_b: Tensor) -> Tensor:
        """
        Symmetric contrastive loss between two modality embeddings.
        emb_a and emb_b must be paired (same index = same concept).
        """
        logit_scale = self.logit_scale.exp().clamp(max=100.0)
        sim = logit_scale * torch.mm(emb_a, emb_b.t())
        labels = torch.arange(emb_a.shape[0], device=emb_a.device)
        loss_ab = F.cross_entropy(sim, labels)
        loss_ba = F.cross_entropy(sim.t(), labels)
        return (loss_ab + loss_ba) / 2.0
