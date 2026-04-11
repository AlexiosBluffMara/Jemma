package ai.jemma.mobile

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class ProviderHealth(
    val provider: String,
    val ok: Boolean,
    val detail: String,
    val models: List<String> = emptyList(),
)

data class HealthEnvelope(
    val ok: Boolean,
    val provider: ProviderHealth,
)

data class ModelSpec(
    val model_id: String,
    val provider: String,
    val remote_name: String,
    val context_window: Int,
    val quantization: String? = null,
    val tags: List<String> = emptyList(),
)

data class ModelsEnvelope(
    val models: List<ModelSpec> = emptyList(),
)

data class ChatMessage(
    val role: String,
    val content: String,
)

data class ChatRequestBody(
    val model: String? = null,
    val system: String = "",
    val messages: List<ChatMessage>,
    val options: Map<String, @JvmSuppressWildcards Any> = emptyMap(),
    val response_format: String? = null,
    val timeout_s: Int = 120,
)

data class ChatResponseBody(
    val model: String,
    val content: String,
    val raw: Map<String, Any?> = emptyMap(),
    val total_duration_ms: Int? = null,
    val prompt_eval_count: Int? = null,
    val eval_count: Int? = null,
)

data class CapabilityDescriptor(
    val name: String,
    val actions: List<String> = emptyList(),
    val allowlisted_targets: List<String> = emptyList(),
    val require_confirmation: Boolean = true,
    val summary: String = "",
)

data class CapabilityEnvelope(
    val capabilities: List<CapabilityDescriptor> = emptyList(),
)

data class BenchmarkPreset(
    val name: String,
    val kind: String,
    val manifest_path: String,
)

data class PresetsEnvelope(
    val presets: List<BenchmarkPreset> = emptyList(),
)

data class JobRecord(
    val job_id: String,
    val kind: String,
    val status: String,
    val visibility: String,
    val created_at: String,
    val started_at: String? = null,
    val finished_at: String? = null,
    val current_phase: String,
    val total_steps: Int,
    val completed_steps: Int,
    val models: List<String> = emptyList(),
    val run_ids: List<String> = emptyList(),
    val prompt_style: String,
    val error: String? = null,
    val summary: Map<String, Any?> = emptyMap(),
)

data class JobsEnvelope(
    val jobs: List<JobRecord> = emptyList(),
)

data class RunRecord(
    val run_id: String,
    val kind: String,
    val name: String,
    val created_at: String,
    val artifact_dir: String,
)

data class RunsEnvelope(
    val runs: List<RunRecord> = emptyList(),
)

data class SystemPayload(
    val captured_at: String,
    val system_probe: Map<String, Any?> = emptyMap(),
    val process: Map<String, Any?>? = null,
    val gpu_runtime: Map<String, Any?>? = null,
)

data class SoloBenchmarkRequest(
    val name: String,
    val models: List<String>,
    val dataset_path: String,
    val repetitions: Int,
    val warmup_runs: Int,
    val visibility: String = "local",
    val options: Map<String, @JvmSuppressWildcards Any> = emptyMap(),
)

data class PairwiseBenchmarkRequest(
    val name: String,
    val left_model: String,
    val right_model: String,
    val dataset_path: String,
    val repetitions: Int,
    val warmup_runs: Int,
    val visibility: String = "local",
    val options: Map<String, @JvmSuppressWildcards Any> = emptyMap(),
)

data class StressBenchmarkRequest(
    val name: String,
    val models: List<String>,
    val standard_dataset_path: String,
    val reasoning_dataset_path: String,
    val repetitions: Int,
    val warmup_runs: Int,
    val visibility: String = "local",
    val options: Map<String, @JvmSuppressWildcards Any> = emptyMap(),
)

data class JobEnvelope(
    val job: JobRecord,
)

interface JemmaApiService {
    @GET("api/health")
    suspend fun getHealth(): HealthEnvelope

    @GET("api/models")
    suspend fun getModels(): ModelsEnvelope

    @GET("api/system")
    suspend fun getSystem(): SystemPayload

    @GET("api/capabilities")
    suspend fun getCapabilities(): CapabilityEnvelope

    @GET("api/benchmarks/presets")
    suspend fun getPresets(): PresetsEnvelope

    @GET("api/jobs")
    suspend fun getJobs(): JobsEnvelope

    @GET("api/runs")
    suspend fun getRuns(): RunsEnvelope

    @POST("api/chat")
    suspend fun chat(@Body body: ChatRequestBody): ChatResponseBody

    @POST("api/jobs/benchmark/solo")
    suspend fun submitSolo(@Body body: SoloBenchmarkRequest): JobEnvelope

    @POST("api/jobs/benchmark/pairwise")
    suspend fun submitPairwise(@Body body: PairwiseBenchmarkRequest): JobEnvelope

    @POST("api/jobs/benchmark/stress")
    suspend fun submitStress(@Body body: StressBenchmarkRequest): JobEnvelope
}

class BackendSettings(context: Context) {
    private val preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var baseUrl: String = normalizeBaseUrl(
        preferences.getString(KEY_BASE_URL, DEFAULT_BASE_URL).orEmpty()
    )
        private set

    fun updateBaseUrl(value: String): String {
        baseUrl = normalizeBaseUrl(value)
        preferences.edit().putString(KEY_BASE_URL, baseUrl).apply()
        return baseUrl
    }

    companion object {
        private const val PREFS_NAME = "jemma-mobile"
        private const val KEY_BASE_URL = "base-url"
        const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"

        fun normalizeBaseUrl(value: String): String {
            val trimmed = value.trim().ifEmpty { DEFAULT_BASE_URL }
            val withoutApiSuffix = trimmed.removeSuffix("/").removeSuffix("/api")
            return if (withoutApiSuffix.endsWith("/")) withoutApiSuffix else "$withoutApiSuffix/"
        }
    }
}

class JemmaRepository {
    private fun service(baseUrl: String): JemmaApiService {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .build()

        return Retrofit.Builder()
            .baseUrl(BackendSettings.normalizeBaseUrl(baseUrl))
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(JemmaApiService::class.java)
    }

    suspend fun getHealth(baseUrl: String): HealthEnvelope = service(baseUrl).getHealth()
    suspend fun getModels(baseUrl: String): ModelsEnvelope = service(baseUrl).getModels()
    suspend fun getSystem(baseUrl: String): SystemPayload = service(baseUrl).getSystem()
    suspend fun getCapabilities(baseUrl: String): CapabilityEnvelope = service(baseUrl).getCapabilities()
    suspend fun getPresets(baseUrl: String): PresetsEnvelope = service(baseUrl).getPresets()
    suspend fun getJobs(baseUrl: String): JobsEnvelope = service(baseUrl).getJobs()
    suspend fun getRuns(baseUrl: String): RunsEnvelope = service(baseUrl).getRuns()
    suspend fun chat(baseUrl: String, body: ChatRequestBody): ChatResponseBody = service(baseUrl).chat(body)
    suspend fun submitSolo(baseUrl: String, body: SoloBenchmarkRequest): JobEnvelope = service(baseUrl).submitSolo(body)
    suspend fun submitPairwise(baseUrl: String, body: PairwiseBenchmarkRequest): JobEnvelope =
        service(baseUrl).submitPairwise(body)

    suspend fun submitStress(baseUrl: String, body: StressBenchmarkRequest): JobEnvelope = service(baseUrl).submitStress(body)
}
