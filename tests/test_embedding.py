"""
Tests for Jemma Embed — Trimodal Gemma 4 Embedding Model

Tests the core embedding model, loss functions, data pipeline,
and benchmark utilities without requiring GPU or real model weights.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
import torch.nn.functional as F

from jemma.embed.model import (
    CrossModalContrastiveLoss,
    EmbedConfig,
    InfoNCELoss,
    JemmaEmbedModel,
    MatryoshkaHead,
    MatryoshkaLoss,
    _pool_last_token,
    _pool_mean,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def embed_config():
    return EmbedConfig(
        model_name="test-model",
        embed_dim=128,
        matryoshka_dims=[32, 64, 128],
        max_seq_length=256,
    )


@pytest.fixture
def random_embeddings():
    """Generate random L2-normalized embedding pairs."""
    batch_size = 16
    dim = 128
    q = F.normalize(torch.randn(batch_size, dim), p=2, dim=-1)
    p = F.normalize(torch.randn(batch_size, dim), p=2, dim=-1)
    n = F.normalize(torch.randn(batch_size * 3, dim), p=2, dim=-1)
    return q, p, n


# ---------------------------------------------------------------------------
# Pooling tests
# ---------------------------------------------------------------------------
class TestPooling:
    def test_last_token_pooling(self):
        hidden = torch.randn(2, 10, 64)  # batch=2, seq=10, dim=64
        mask = torch.ones(2, 10)
        mask[1, 7:] = 0  # Second sequence has length 7

        pooled = _pool_last_token(hidden, mask)
        assert pooled.shape == (2, 64)
        # First sequence: last token is index 9
        assert torch.allclose(pooled[0], hidden[0, 9])
        # Second sequence: last non-pad token is index 6
        assert torch.allclose(pooled[1], hidden[1, 6])

    def test_mean_pooling(self):
        hidden = torch.ones(2, 5, 32)
        mask = torch.ones(2, 5)
        mask[1, 3:] = 0

        pooled = _pool_mean(hidden, mask)
        assert pooled.shape == (2, 32)
        # All ones → mean should be ones
        assert torch.allclose(pooled[0], torch.ones(32))
        assert torch.allclose(pooled[1], torch.ones(32))

    def test_mean_pooling_varied(self):
        hidden = torch.zeros(1, 4, 8)
        hidden[0, 0] = 2.0
        hidden[0, 1] = 4.0
        mask = torch.tensor([[1, 1, 0, 0]], dtype=torch.float)

        pooled = _pool_mean(hidden, mask)
        expected = torch.full((8,), 3.0)  # (2+4)/2
        assert torch.allclose(pooled[0], expected)


# ---------------------------------------------------------------------------
# MatryoshkaHead tests
# ---------------------------------------------------------------------------
class TestMatryoshkaHead:
    def test_identity_projection(self):
        head = MatryoshkaHead(128, [32, 64, 128])
        x = torch.randn(4, 128)
        out = head(x)
        assert out.shape == (4, 128)
        # Identity projection — should be same
        assert torch.allclose(out, x)

    def test_learned_projection(self):
        head = MatryoshkaHead(128, [32, 64, 256])
        x = torch.randn(4, 128)
        out = head(x)
        assert out.shape == (4, 256)

    def test_truncation(self):
        head = MatryoshkaHead(128, [32, 64, 128])
        x = torch.randn(4, 128)
        trunc = head.truncate(x, 32)
        assert trunc.shape == (4, 32)
        trunc64 = head.truncate(x, 64)
        assert trunc64.shape == (4, 64)


# ---------------------------------------------------------------------------
# Loss function tests
# ---------------------------------------------------------------------------
class TestInfoNCELoss:
    def test_basic_loss(self, random_embeddings):
        q, p, _ = random_embeddings
        loss_fn = InfoNCELoss(temperature=0.02)
        loss = loss_fn(q, p)
        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_perfect_match_low_loss(self):
        """Identical embeddings should give lower loss than random."""
        dim = 64
        batch = 8
        emb = F.normalize(torch.randn(batch, dim), dim=-1)
        loss_fn = InfoNCELoss(temperature=0.07)

        # Perfect match
        loss_perfect = loss_fn(emb, emb.clone())
        # Random
        loss_random = loss_fn(emb, F.normalize(torch.randn(batch, dim), dim=-1))

        assert loss_perfect < loss_random

    def test_with_hard_negatives(self, random_embeddings):
        q, p, n = random_embeddings
        loss_fn = InfoNCELoss(temperature=0.02)
        loss_with_neg = loss_fn(q, p, n)
        loss_without_neg = loss_fn(q, p)
        # With hard negatives, loss should generally be >= without
        assert loss_with_neg.item() > 0
        assert not torch.isnan(loss_with_neg)

    def test_temperature_effect(self, random_embeddings):
        q, p, _ = random_embeddings
        loss_low_temp = InfoNCELoss(temperature=0.01)(q, p)
        loss_high_temp = InfoNCELoss(temperature=1.0)(q, p)
        # Lower temperature → sharper distribution → different loss
        assert loss_low_temp.item() != loss_high_temp.item()


class TestMatryoshkaLoss:
    def test_multi_dim_loss(self, random_embeddings):
        q, p, _ = random_embeddings
        base = InfoNCELoss(temperature=0.02)
        loss_fn = MatryoshkaLoss(base, [32, 64, 128])
        loss = loss_fn(q, p)
        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_weights_sum_to_one(self):
        base = InfoNCELoss()
        loss_fn = MatryoshkaLoss(base, [32, 64, 128])
        assert abs(sum(loss_fn.dim_weights) - 1.0) < 1e-6

    def test_custom_weights(self, random_embeddings):
        q, p, _ = random_embeddings
        base = InfoNCELoss(temperature=0.02)
        loss_fn = MatryoshkaLoss(base, [32, 64, 128],
                                 dim_weights=[1.0, 1.0, 1.0])
        loss = loss_fn(q, p)
        assert loss.item() > 0


class TestCrossModalLoss:
    def test_symmetric_loss(self):
        dim = 64
        batch = 8
        emb_a = F.normalize(torch.randn(batch, dim), dim=-1)
        emb_b = F.normalize(torch.randn(batch, dim), dim=-1)
        loss_fn = CrossModalContrastiveLoss(temperature=0.07)
        loss = loss_fn(emb_a, emb_b)
        assert loss.item() > 0
        assert not torch.isnan(loss)

    def test_perfect_alignment(self):
        dim = 64
        batch = 8
        emb = F.normalize(torch.randn(batch, dim), dim=-1)
        loss_fn = CrossModalContrastiveLoss(temperature=0.07)
        loss_perfect = loss_fn(emb, emb.clone())
        loss_random = loss_fn(emb, F.normalize(torch.randn(batch, dim), dim=-1))
        assert loss_perfect < loss_random

    def test_learnable_logit_scale(self):
        loss_fn = CrossModalContrastiveLoss()
        params = list(loss_fn.parameters())
        assert len(params) == 1  # logit_scale


# ---------------------------------------------------------------------------
# EmbedConfig tests
# ---------------------------------------------------------------------------
class TestEmbedConfig:
    def test_defaults(self, embed_config):
        assert embed_config.pooling == "last_token"
        assert embed_config.normalize is True
        assert embed_config.quantization_bits == 4

    def test_matryoshka_dims_sorted(self, embed_config):
        assert embed_config.matryoshka_dims == sorted(embed_config.matryoshka_dims)


# ---------------------------------------------------------------------------
# Data pipeline tests
# ---------------------------------------------------------------------------
class TestDataPipeline:
    def test_chunk_text(self):
        from pipeline.embedding_data import _chunk_text
        text = "Short text."
        chunks = _chunk_text(text, max_chars=512)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_long_text(self):
        from pipeline.embedding_data import _chunk_text
        text = "A " * 1000  # ~2000 chars
        chunks = _chunk_text(text, max_chars=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 250  # Allow some overflow for boundary finding

    def test_text_triplet_dataset(self, tmp_path):
        from pipeline.embedding_data import TextTripletDataset

        # Create test data
        data_file = tmp_path / "test.jsonl"
        records = [
            {"type": "triplet", "query": "q1", "positive": "p1", "negative": "n1"},
            {"type": "pair", "anchor": "a1", "positive": "p2"},
        ]
        with open(data_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        ds = TextTripletDataset([data_file])
        assert len(ds) == 2

        item = ds[0]
        assert item["query"] == "q1"
        assert item["positive"] == "p1"
        assert item["negative"] == "n1"

        item2 = ds[1]
        assert item2["query"] == "a1"
        assert item2["positive"] == "p2"

    def test_multimodal_pair_dataset(self, tmp_path):
        from pipeline.embedding_data import MultimodalPairDataset

        data_file = tmp_path / "test_mm.jsonl"
        records = [
            {"type": "image_text_pair", "caption": "a cat", "index": 0},
            {"type": "image_text_pair", "caption": "a dog", "index": 1},
        ]
        with open(data_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        ds = MultimodalPairDataset(data_file, modality="image_text")
        assert len(ds) == 2
        assert ds[0]["caption"] == "a cat"
        assert ds[0]["modality"] == "image_text"


# ---------------------------------------------------------------------------
# JemmaEmbedModel tests (mock backbone)
# ---------------------------------------------------------------------------
class TestJemmaEmbedModel:
    def test_model_creation(self, embed_config):
        model = JemmaEmbedModel(embed_config)
        assert model.config.embed_dim == 128
        assert model.matryoshka_head is not None

    def test_matryoshka_head_dims(self, embed_config):
        model = JemmaEmbedModel(embed_config)
        x = torch.randn(4, 128)
        for dim in [32, 64, 128]:
            out = model.matryoshka_head.truncate(x, dim)
            assert out.shape == (4, dim)

    def test_encode_with_mock_backbone(self, embed_config):
        model = JemmaEmbedModel(embed_config)

        # Mock backbone that returns hidden states
        mock_output = MagicMock()
        mock_output.hidden_states = [torch.randn(2, 10, 128)]

        model.backbone = MagicMock()
        model.backbone.device = torch.device("cpu")
        model.backbone.return_value = mock_output
        model.backbone.__call__ = MagicMock(return_value=mock_output)

        input_ids = torch.randint(0, 1000, (2, 10))
        attention_mask = torch.ones(2, 10)

        emb = model.encode(input_ids, attention_mask)
        assert emb.shape == (2, 128)
        # Should be L2-normalized
        norms = torch.norm(emb, dim=-1)
        assert torch.allclose(norms, torch.ones(2), atol=1e-5)


# ---------------------------------------------------------------------------
# Config loading test
# ---------------------------------------------------------------------------
class TestConfig:
    def test_config_file_exists(self):
        config_path = Path(__file__).parent.parent / "configs" / "embedding-training.toml"
        assert config_path.exists(), f"Config file missing: {config_path}"

    def test_config_loads(self):
        import tomllib
        config_path = Path(__file__).parent.parent / "configs" / "embedding-training.toml"
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        assert "models" in config
        assert "e2b" in config["models"]
        assert "e4b" in config["models"]
        assert "training" in config
        assert "qlora" in config
        assert config["models"]["e2b"]["embed_dim"] == 2304
        assert config["models"]["e4b"]["embed_dim"] == 3072


# ---------------------------------------------------------------------------
# Integration-style test (no GPU needed)
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_loss_backward_pass(self):
        """Verify full forward + backward through loss functions."""
        dim = 64
        batch = 8

        q = torch.randn(batch, dim, requires_grad=True)
        p = torch.randn(batch, dim, requires_grad=True)

        q_norm = F.normalize(q, dim=-1)
        p_norm = F.normalize(p, dim=-1)

        loss_fn = InfoNCELoss(temperature=0.05)
        loss = loss_fn(q_norm, p_norm)
        loss.backward()

        assert q.grad is not None
        assert p.grad is not None

    def test_matryoshka_backward(self):
        """Verify Matryoshka loss backward pass."""
        dim = 128
        batch = 8

        q = torch.randn(batch, dim, requires_grad=True)
        p = torch.randn(batch, dim, requires_grad=True)

        base = InfoNCELoss(temperature=0.05)
        loss_fn = MatryoshkaLoss(base, [32, 64, 128])
        loss = loss_fn(
            F.normalize(q, dim=-1),
            F.normalize(p, dim=-1),
        )
        loss.backward()

        assert q.grad is not None

    def test_cross_modal_backward(self):
        """Verify cross-modal loss backward."""
        dim = 64
        batch = 8

        a = torch.randn(batch, dim, requires_grad=True)
        b = torch.randn(batch, dim, requires_grad=True)

        loss_fn = CrossModalContrastiveLoss(temperature=0.07)
        loss = loss_fn(
            F.normalize(a, dim=-1),
            F.normalize(b, dim=-1),
        )
        loss.backward()

        assert a.grad is not None
        assert b.grad is not None
