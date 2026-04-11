package ai.jemma.mobile

import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.BuildCircle
import androidx.compose.material.icons.outlined.Chat
import androidx.compose.material.icons.outlined.Dashboard
import androidx.compose.material.icons.outlined.Memory
import androidx.compose.material.icons.outlined.ModelTraining
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Speed
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.windowsizeclass.WindowWidthSizeClass
import androidx.compose.material3.windowsizeclass.calculateWindowSizeClass
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import ai.jemma.mobile.ui.theme.JemmaTheme
import kotlinx.coroutines.async
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val windowSizeClass = calculateWindowSizeClass(this)
            JemmaTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    JemmaApp(windowSizeClass = windowSizeClass.widthSizeClass)
                }
            }
        }
    }
}

private enum class JemmaScreen(
    val label: String,
    val icon: ImageVector,
) {
    Home("Home", Icons.Outlined.Dashboard),
    Chat("Chat", Icons.Outlined.Chat),
    PromptLab("Prompt Lab", Icons.Outlined.Tune),
    Skills("Skills", Icons.Outlined.BuildCircle),
    Benchmarks("Benchmarks", Icons.Outlined.Speed),
    Models("Models", Icons.Outlined.ModelTraining),
    System("System", Icons.Outlined.Memory),
}

private data class UiMessage(
    val role: String,
    val content: String,
)

private data class SurfaceTile(
    val title: String,
    val value: String,
    val detail: String,
)

private class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = BackendSettings(application)
    private val repository = JemmaRepository()

    var baseUrl by mutableStateOf(settings.baseUrl)
        private set
    var statusMessage by mutableStateOf("Remote-first mobile control plane")
        private set
    var loading by mutableStateOf(false)
        private set
    var health by mutableStateOf<ProviderHealth?>(null)
        private set
    var models by mutableStateOf<List<ModelSpec>>(emptyList())
        private set
    var capabilities by mutableStateOf<List<CapabilityDescriptor>>(emptyList())
        private set
    var presets by mutableStateOf<List<BenchmarkPreset>>(emptyList())
        private set
    var jobs by mutableStateOf<List<JobRecord>>(emptyList())
        private set
    var runs by mutableStateOf<List<RunRecord>>(emptyList())
        private set
    var system by mutableStateOf<SystemPayload?>(null)
        private set
    var selectedModelId by mutableStateOf("")
        private set
    val chatMessages = mutableStateListOf<UiMessage>()
    var promptLabOutput by mutableStateOf("")
        private set
    var promptLabMode by mutableStateOf("Structured Brief")
        private set

    init {
        refreshAll()
    }

    fun saveBaseUrl(value: String) {
        baseUrl = settings.updateBaseUrl(value)
        statusMessage = "Saved backend: $baseUrl"
        refreshAll()
    }

    fun setSelectedModel(modelId: String) {
        selectedModelId = modelId
    }

    fun setPromptLabMode(mode: String) {
        promptLabMode = mode
    }

    fun refreshAll() {
        viewModelScope.launch {
            loading = true
            statusMessage = "Refreshing backend state"
            runCatching {
                val currentBaseUrl = baseUrl
                val healthDeferred = async { repository.getHealth(currentBaseUrl) }
                val modelsDeferred = async { repository.getModels(currentBaseUrl) }
                val capabilitiesDeferred = async { repository.getCapabilities(currentBaseUrl) }
                val presetsDeferred = async { repository.getPresets(currentBaseUrl) }
                val jobsDeferred = async { repository.getJobs(currentBaseUrl) }
                val runsDeferred = async { repository.getRuns(currentBaseUrl) }
                val systemDeferred = async { repository.getSystem(currentBaseUrl) }

                health = healthDeferred.await().provider
                models = modelsDeferred.await().models
                capabilities = capabilitiesDeferred.await().capabilities
                presets = presetsDeferred.await().presets
                jobs = jobsDeferred.await().jobs
                runs = runsDeferred.await().runs
                system = systemDeferred.await()
                if (selectedModelId.isBlank()) {
                    selectedModelId = preferredPrimaryModel(models)?.model_id.orEmpty()
                }
            }.onSuccess {
                statusMessage = "Connected to ${health?.provider ?: "backend"}"
            }.onFailure { error ->
                statusMessage = error.message ?: "Unable to reach backend"
            }
            loading = false
        }
    }

    fun sendChat(prompt: String) {
        val trimmed = prompt.trim()
        if (trimmed.isEmpty()) return
        val modelId = selectedModelId.ifBlank { preferredPrimaryModel(models)?.model_id.orEmpty() }
        chatMessages += UiMessage("user", trimmed)
        statusMessage = "Sending chat request"
        viewModelScope.launch {
            runCatching {
                repository.chat(
                    baseUrl = baseUrl,
                    body = ChatRequestBody(
                        model = modelId.ifBlank { null },
                        messages = chatMessages.map { ChatMessage(role = it.role, content = it.content) },
                    ),
                )
            }.onSuccess { response ->
                chatMessages += UiMessage("assistant", response.content)
                statusMessage = "Chat response from ${response.model}"
            }.onFailure { error ->
                chatMessages += UiMessage("assistant", "Request failed: ${error.message}")
                statusMessage = "Chat failed"
            }
        }
    }

    fun runPromptLab(prompt: String) {
        val trimmed = prompt.trim()
        if (trimmed.isEmpty()) return
        val systemPrompt = when (promptLabMode) {
            "JSON Plan" -> "Return valid JSON with keys goal, constraints, plan, risks."
            "Safety Check" -> "Review the prompt for safety, operational risk, and missing guardrails."
            else -> "Create a concise structured brief with bullets and next actions."
        }
        val responseFormat = if (promptLabMode == "JSON Plan") "json" else null
        statusMessage = "Running prompt lab"
        viewModelScope.launch {
            runCatching {
                repository.chat(
                    baseUrl = baseUrl,
                    body = ChatRequestBody(
                        model = selectedModelId.ifBlank { null },
                        system = systemPrompt,
                        messages = listOf(ChatMessage(role = "user", content = trimmed)),
                        response_format = responseFormat,
                    ),
                )
            }.onSuccess { response ->
                promptLabOutput = response.content
                statusMessage = "Prompt lab updated"
            }.onFailure { error ->
                promptLabOutput = "Request failed: ${error.message}"
                statusMessage = "Prompt lab failed"
            }
        }
    }

    fun launchStressBenchmark() {
        val modelPool = models.take(3).map { it.model_id }
        if (modelPool.isEmpty()) return
        statusMessage = "Launching stress benchmark"
        viewModelScope.launch {
            runCatching {
                repository.submitStress(
                    baseUrl,
                    StressBenchmarkRequest(
                        name = "android-stress-benchmark",
                        models = modelPool,
                        standard_dataset_path = "datasets/prompts/stress-standard.jsonl",
                        reasoning_dataset_path = "datasets/prompts/stress-reasoning.jsonl",
                        repetitions = 1,
                        warmup_runs = 1,
                        options = mapOf("temperature" to 0),
                    ),
                )
            }.onSuccess {
                statusMessage = "Stress benchmark submitted"
                refreshAll()
            }.onFailure { error ->
                statusMessage = error.message ?: "Failed to submit stress benchmark"
            }
        }
    }

    fun launchSoloBenchmark() {
        val modelPool = models.take(2).map { it.model_id }
        if (modelPool.isEmpty()) return
        statusMessage = "Launching solo benchmark"
        viewModelScope.launch {
            runCatching {
                repository.submitSolo(
                    baseUrl,
                    SoloBenchmarkRequest(
                        name = "android-solo-benchmark",
                        models = modelPool,
                        dataset_path = "datasets/prompts/smoke.jsonl",
                        repetitions = 1,
                        warmup_runs = 1,
                        options = mapOf("temperature" to 0),
                    ),
                )
            }.onSuccess {
                statusMessage = "Solo benchmark submitted"
                refreshAll()
            }.onFailure { error ->
                statusMessage = error.message ?: "Failed to submit solo benchmark"
            }
        }
    }

    fun launchPairwiseBenchmark() {
        val left = models.firstOrNull()?.model_id ?: return
        val right = models.getOrNull(1)?.model_id ?: left
        statusMessage = "Launching pairwise benchmark"
        viewModelScope.launch {
            runCatching {
                repository.submitPairwise(
                    baseUrl,
                    PairwiseBenchmarkRequest(
                        name = "android-pairwise-benchmark",
                        left_model = left,
                        right_model = right,
                        dataset_path = "datasets/prompts/qa.jsonl",
                        repetitions = 1,
                        warmup_runs = 1,
                        options = mapOf("temperature" to 0),
                    ),
                )
            }.onSuccess {
                statusMessage = "Pairwise benchmark submitted"
                refreshAll()
            }.onFailure { error ->
                statusMessage = error.message ?: "Failed to submit pairwise benchmark"
            }
        }
    }

    fun surfaceTiles(): List<SurfaceTile> = listOf(
        SurfaceTile(
            title = "Surface benchmark",
            value = "7 / 7",
            detail = "Home, Chat, Prompt Lab, Skills, Benchmarks, Models, System aligned to a clean public AI Edge Gallery-style surface.",
        ),
        SurfaceTile(
            title = "Primary path",
            value = preferredPrimaryModel(models)?.remote_name ?: "Awaiting models",
            detail = "Remote-first E4B on workstation remains the default quality path.",
        ),
        SurfaceTile(
            title = "Fallback stance",
            value = models.firstOrNull { "fallback" in it.tags }?.remote_name ?: "Later",
            detail = "E2B fallback is treated as later offline work, not workstation parity.",
        ),
        SurfaceTile(
            title = "Skills exposed",
            value = capabilities.size.toString(),
            detail = "Read-only and confirmation-gated capability summaries from the backend registry.",
        ),
        SurfaceTile(
            title = "Benchmarks ready",
            value = presets.size.toString(),
            detail = "Preset benchmark launches and recent runs stay available from mobile.",
        ),
        SurfaceTile(
            title = "System telemetry",
            value = if (health?.ok == true) "Healthy" else "Degraded",
            detail = "Provider health, process metrics, and GPU runtime flow through the backend API.",
        ),
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun JemmaApp(
    windowSizeClass: WindowWidthSizeClass,
    viewModel: MainViewModel = viewModel(),
) {
    var selectedScreen by rememberSaveable { mutableStateOf(JemmaScreen.Home) }
    val useRail = windowSizeClass != WindowWidthSizeClass.Compact
    val screens = JemmaScreen.entries

    Scaffold(
        contentWindowInsets = WindowInsets.safeDrawing,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Jemma Mobile", fontWeight = FontWeight.SemiBold)
                        Text(
                            text = viewModel.statusMessage,
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    TextButton(onClick = viewModel::refreshAll) {
                        androidx.compose.material3.Icon(Icons.Outlined.Refresh, contentDescription = "Refresh")
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Refresh")
                    }
                },
            )
        },
        bottomBar = {
            if (!useRail) {
                NavigationBar {
                    screens.forEach { screen ->
                        NavigationBarItem(
                            selected = selectedScreen == screen,
                            onClick = { selectedScreen = screen },
                            icon = { androidx.compose.material3.Icon(screen.icon, contentDescription = screen.label) },
                            label = { Text(screen.label) },
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            if (useRail) {
                NavigationRail(modifier = Modifier.fillMaxHeight()) {
                    screens.forEach { screen ->
                        NavigationRailItem(
                            selected = selectedScreen == screen,
                            onClick = { selectedScreen = screen },
                            icon = { androidx.compose.material3.Icon(screen.icon, contentDescription = screen.label) },
                            label = { Text(screen.label) },
                        )
                    }
                }
            }

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.background),
            ) {
                when (selectedScreen) {
                    JemmaScreen.Home -> HomeScreen(viewModel)
                    JemmaScreen.Chat -> ChatScreen(viewModel)
                    JemmaScreen.PromptLab -> PromptLabScreen(viewModel)
                    JemmaScreen.Skills -> SkillsScreen(viewModel)
                    JemmaScreen.Benchmarks -> BenchmarksScreen(viewModel)
                    JemmaScreen.Models -> ModelsScreen(viewModel)
                    JemmaScreen.System -> SystemScreen(viewModel)
                }
            }
        }
    }
}

@Composable
private fun HomeScreen(viewModel: MainViewModel) {
    val tiles = viewModel.surfaceTiles()
    Column(modifier = Modifier.fillMaxSize()) {
        if (viewModel.loading) {
            LinearLoadingBanner()
        }
        LazyVerticalGrid(
            columns = GridCells.Adaptive(220.dp),
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(tiles) { tile ->
                MetricCard(title = tile.title, value = tile.value, detail = tile.detail)
            }
        }
    }
}

@Composable
private fun ChatScreen(viewModel: MainViewModel) {
    var draft by rememberSaveable { mutableStateOf("") }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ScreenIntro(
            title = "Chat",
            body = "Remote-first conversation over the Jemma backend. This surface does not claim unvalidated on-device multimodal or tool parity.",
        )
        ModelSelector(models = viewModel.models, selectedModelId = viewModel.selectedModelId, onSelect = viewModel::setSelectedModel)
        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(viewModel.chatMessages.size) { index ->
                val message = viewModel.chatMessages[index]
                MessageBubble(message)
            }
        }
        OutlinedTextField(
            value = draft,
            onValueChange = { draft = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Prompt") },
            minLines = 3,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = {
                viewModel.sendChat(draft)
                draft = ""
            }) {
                Text("Send")
            }
            OutlinedButton(onClick = viewModel::refreshAll) {
                Text("Refresh")
            }
        }
    }
}

@Composable
private fun PromptLabScreen(viewModel: MainViewModel) {
    var prompt by rememberSaveable { mutableStateOf("") }
    val modes = listOf("Structured Brief", "JSON Plan", "Safety Check")
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ScreenIntro(
            title = "Prompt Lab",
            body = "Quick prompt experiments against the workstation path. JSON mode uses the backend chat contract rather than any unverified mobile-native tool stack.",
        )
        ModelSelector(models = viewModel.models, selectedModelId = viewModel.selectedModelId, onSelect = viewModel::setSelectedModel)
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(modes.size) { index ->
                val mode = modes[index]
                FilterChip(
                    selected = viewModel.promptLabMode == mode,
                    onClick = { viewModel.setPromptLabMode(mode) },
                    label = { Text(mode) },
                )
            }
        }
        OutlinedTextField(
            value = prompt,
            onValueChange = { prompt = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Prompt input") },
            minLines = 4,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { viewModel.runPromptLab(prompt) }) {
                Text("Run")
            }
            OutlinedButton(onClick = { prompt = "" }) {
                Text("Clear")
            }
        }
        InfoCard(
            title = "Output",
            body = if (viewModel.promptLabOutput.isBlank()) "Run a prompt to populate this panel." else viewModel.promptLabOutput,
        )
    }
}

@Composable
private fun SkillsScreen(viewModel: MainViewModel) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            ScreenIntro(
                title = "Skills",
                body = "Capability summaries are sourced from the backend registry and policy configuration."
            )
        }
        items(viewModel.capabilities.size) { index ->
            val capability = viewModel.capabilities[index]
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(capability.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(capability.summary, style = MaterialTheme.typography.bodyMedium)
                    FlowRowChips(capability.actions)
                    Text(
                        if (capability.require_confirmation) "Confirmation required for sensitive actions." else "Read-only or low-risk observation path.",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (capability.allowlisted_targets.isNotEmpty()) {
                        Text(
                            "Allowlisted: ${capability.allowlisted_targets.joinToString()}",
                            style = MaterialTheme.typography.labelMedium,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun BenchmarksScreen(viewModel: MainViewModel) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            ScreenIntro(
                title = "Benchmarks",
                body = "Submit the minimum mobile benchmark flows already supported by the backend job APIs."
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = viewModel::launchStressBenchmark) { Text("Stress") }
                OutlinedButton(onClick = viewModel::launchSoloBenchmark) { Text("Solo") }
                OutlinedButton(onClick = viewModel::launchPairwiseBenchmark) { Text("Pairwise") }
            }
        }
        item {
            InfoCard(
                title = "Presets",
                body = viewModel.presets.joinToString(separator = "\n") { "${it.name} (${it.kind})" }.ifBlank { "No presets available." },
            )
        }
        item {
            SectionLabel("Recent jobs")
        }
        items(viewModel.jobs.take(6).size) { index ->
            val job = viewModel.jobs[index]
            SummaryCard(
                title = job.kind.replaceFirstChar { it.uppercase() } + " • " + job.status,
                subtitle = job.job_id,
                detail = "Phase: ${job.current_phase}\nModels: ${job.models.joinToString()}",
            )
        }
        item {
            SectionLabel("Recent runs")
        }
        items(viewModel.runs.take(6).size) { index ->
            val run = viewModel.runs[index]
            SummaryCard(
                title = run.name,
                subtitle = run.kind,
                detail = "Run ID: ${run.run_id}\nArtifact dir: ${run.artifact_dir}",
            )
        }
    }
}

@Composable
private fun ModelsScreen(viewModel: MainViewModel) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            ScreenIntro(
                title = "Models",
                body = "Remote-first E4B stays primary. E2B fallback is listed for later offline usage only."
            )
        }
        items(viewModel.models.size) { index ->
            val model = viewModel.models[index]
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(model.model_id, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(model.remote_name, style = MaterialTheme.typography.bodyMedium)
                    Text("Context window: ${model.context_window}", style = MaterialTheme.typography.bodySmall)
                    Text("Quantization: ${model.quantization ?: "n/a"}", style = MaterialTheme.typography.bodySmall)
                    FlowRowChips(model.tags)
                }
            }
        }
    }
}

@Composable
private fun SystemScreen(viewModel: MainViewModel) {
    var draftUrl by remember(viewModel.baseUrl) { mutableStateOf(viewModel.baseUrl) }
    val process = viewModel.system?.process ?: emptyMap()
    val gpu = viewModel.system?.gpu_runtime ?: emptyMap()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(bottom = 24.dp + WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()),
    ) {
        item {
            ScreenIntro(
                title = "System",
                body = "Point this app at the workstation-hosted Jemma API on a trusted network or over adb reverse."
            )
        }
        item {
            OutlinedTextField(
                value = draftUrl,
                onValueChange = { draftUrl = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Backend base URL") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { viewModel.saveBaseUrl(draftUrl) }) { Text("Save URL") }
                OutlinedButton(onClick = viewModel::refreshAll) { Text("Refresh now") }
            }
        }
        item {
            SummaryCard(
                title = "Provider health",
                subtitle = viewModel.health?.provider ?: "Unavailable",
                detail = "Status: ${if (viewModel.health?.ok == true) "healthy" else "degraded"}\nDetail: ${viewModel.health?.detail ?: "n/a"}",
            )
        }
        item {
            SummaryCard(
                title = "Process telemetry",
                subtitle = viewModel.system?.captured_at ?: "Not captured",
                detail = process.entries.joinToString(separator = "\n") { "${it.key}: ${it.value}" }.ifBlank { "No process metrics available." },
            )
        }
        item {
            SummaryCard(
                title = "GPU runtime",
                subtitle = gpu["name"]?.toString() ?: "Unavailable",
                detail = gpu.entries.joinToString(separator = "\n") { "${it.key}: ${it.value}" }.ifBlank { "No GPU metrics available." },
            )
        }
        item {
            InfoCard(
                title = "Scope note",
                body = "This mobile client is a remote-first control surface. It does not promise unvalidated on-device multimodal or tool-calling parity.",
            )
        }
    }
}

@Composable
private fun ScreenIntro(title: String, body: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
        Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ModelSelector(
    models: List<ModelSpec>,
    selectedModelId: String,
    onSelect: (String) -> Unit,
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(models.size) { index ->
            val model = models[index]
            FilterChip(
                selected = selectedModelId == model.model_id,
                onClick = { onSelect(model.model_id) },
                label = { Text(model.model_id) },
            )
        }
    }
}

@Composable
private fun MessageBubble(message: UiMessage) {
    val isUser = message.role == "user"
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (isUser) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                if (isUser) "You" else "Jemma",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(message.content, style = MaterialTheme.typography.bodyLarge)
        }
    }
}

@Composable
private fun MetricCard(title: String, value: String, detail: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun InfoCard(title: String, body: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun SummaryCard(title: String, subtitle: String, detail: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(subtitle, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            Text(detail, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun FlowRowChips(values: List<String>) {
    if (values.isEmpty()) return
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(values.size) { index ->
            AssistChip(onClick = {}, label = { Text(values[index]) })
        }
    }
}

@Composable
private fun SectionLabel(value: String) {
    Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun LinearLoadingBanner() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        CircularProgressIndicator(modifier = Modifier.width(20.dp).height(20.dp), strokeWidth = 2.dp)
        Text("Refreshing…", style = MaterialTheme.typography.bodyMedium)
    }
}

private fun preferredPrimaryModel(models: List<ModelSpec>): ModelSpec? {
    return models.firstOrNull { "default" in it.tags } ?: models.firstOrNull()
}
