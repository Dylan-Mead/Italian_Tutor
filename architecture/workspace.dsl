workspace "Italian Tutor" "C4 software architecture model for the Italian Tutor (\"Paolo\") application: a local, Ollama-backed Italian conversation tutor with a CLI and a home-network web UI." {

    model {
        learner = person "Language Learner" "A person practicing conversational Italian with the AI tutor persona \"Paolo\", via the terminal or a browser on the home network."

        ollama = softwareSystem "Ollama LLM Server" "Local Ollama runtime (not written by this project) that loads and serves the custom LLM models used by the tutor, on the same machine or home network as the tutor application." "External System" {
            tags "External System"
        }

        italianTutor = softwareSystem "Italian Tutor" "Lets a learner practice conversational Italian with an AI tutor persona, tracking vocabulary, mastered grammar concepts and CEFR proficiency across sessions." {

            cli = container "CLI Application" "Terminal-based chat interface for Paolo, installed as the `tutor` command. Supports a free-conversation mode and a structured, single-word-focus mode." "Python" {
                freeModeRepl = component "Free-Mode REPL" "Runs the open-ended conversation loop in the terminal; streams replies and handles /exit, /reset and /structured commands." "Python (tutor.py: main)"
                structuredModeRepl = component "Structured-Mode REPL" "Runs the single-word-focus conversation loop in the terminal; handles /next, /reset, /free and /exit commands." "Python (tutor.py: main_structured)"

                freeModeRepl -> structuredModeRepl "Hands off to, on '/structured'"
                structuredModeRepl -> freeModeRepl "Hands off to, on '/free' (or if no word list is found)"
            }

            webApp = container "Web Application" "Flask server exposing a chat API and serving the browser-based chat UI, installed as the `tutor-web` command. Binds to 0.0.0.0:5000 for access from other devices on the home network." "Python / Flask" {
                flaskRoutes = component "Chat API Routes" "HTTP endpoints for sending a chat message (streamed reply), switching free/structured mode, saving progress, resetting the conversation, and polling the learner's memory." "Flask routes (webapp.py)"
                conversationManager = component "Conversation Manager" "Keeps one in-memory conversation (message history, teaching mode, recent/focus words) per browser, keyed by a session cookie." "Python dict (webapp.py: CONVERSATIONS, get_conversation)"

                flaskRoutes -> conversationManager "Reads and updates the active browser's conversation state via"
            }

            chatUi = container "Chat Web UI" "Single-page chat interface rendered in the learner's browser: message list, structured-mode toggle, and a progress sidebar (level, vocabulary, mastered concepts)." "HTML, CSS, JavaScript" {
                tags "Browser"
            }

            tutorCore = container "Tutor Core Library" "Shared business logic imported by both the CLI and the Web Application: memory persistence, system prompt construction, prompt-injection screening, session scoring and structured-mode word selection." "Python module (italian_tutor.tutor)" {
                memoryManager = component "Memory Manager" "Loads, merges and saves the learner's persistent profile: proficiency level, learned/struggled vocabulary and mastered grammar concepts. Never lets a session lower the recorded CEFR level." "Python (load_memory, save_memory, merge_memory, higher_cefr_level)"
                promptBuilder = component "System Prompt Builder" "Builds the system prompt sent to the tutor LLM by combining a JSON prompt template with the learner's current memory state and, in structured mode, the current focus word." "Python (build_system_prompt, load_system_prompt_template)"
                firewallClient = component "Prompt Firewall Client" "Sends each learner message to the prompt-firewall model before it reaches the tutor model, and blocks the turn unless the verdict is exactly SAFE." "Python (is_input_safe)"
                sessionFinalizer = component "Session Finalizer" "Asks the tutor LLM to assess the conversation against the CEFR level descriptions, parses the JSON verdict, and merges it into the learner's memory via the Memory Manager." "Python (finalize_session, load_cefr_descriptions)"
                wordPicker = component "Structured-Mode Word Picker" "Chooses the next vocabulary focus word using frequency-weighted random selection, avoiding the 10 most recently used words." "Python (load_word_list, pick_word, pick_next_word, update_recent_words)"

                sessionFinalizer -> memoryManager "Merges the session summary into memory via"
            }

            memoryStore = container "User Memory Store" "Single shared JSON file holding one learner profile: proficiency level, vocabulary lists, mastered concepts and session notes. Concurrent devices merge into this file on save/reset, not overwrite it." "JSON file (tutor_memory.json)" {
                tags "Data Store"
            }

            vocabData = container "Vocabulary & CEFR Reference Data" "Static reference data: an Italian word-frequency list used to pick structured-mode focus words, and CEFR level descriptions used to ground the end-of-session proficiency assessment." "CSV files (word_list.csv, CEFR_Levels.csv)" {
                tags "Data Store"
            }

            promptTemplates = container "System Prompt Templates" "JSON templates (default, friendly, structured) describing Paolo's persona, the learner-state fields to inject, and the teaching rules the tutor model must follow." "JSON files" {
                tags "Data Store"
            }

            contentPipeline = container "Vocabulary Content Pipeline" "Offline, maintainer-run scripts that scrape Italian word-frequency data, rank it and export the word list consumed by structured mode. Not part of the running application." "Python scripts / Jupyter notebook" {
                tags "Offline Tooling"
            }

            modelDefinitions = container "Custom Model Definitions" "Ollama Modelfiles, built offline with `ollama create`, that customize base models into Paolo's tutor persona (qwen3:8b) and the prompt-injection firewall (phi4-mini:3.8b)." "Ollama Modelfile" {
                tags "Offline Tooling"
            }

            # Learner entry points
            learner -> freeModeRepl "Chats with Paolo in" "Terminal"
            learner -> chatUi "Chats with Paolo in, and views learning progress via" "Web browser, HTTP"

            # Web UI <-> Web Application
            chatUi -> flaskRoutes "Sends chat messages to and streams replies from; switches mode, saves/resets progress, and polls memory via" "fetch(), JSON over HTTP (streamed for chat replies)"
            flaskRoutes -> chatUi "Serves the chat page and static assets (HTML, CSS, JS) to" "HTTP"

            # CLI -> Tutor Core
            freeModeRepl -> memoryManager "Loads and saves learner memory via"
            freeModeRepl -> promptBuilder "Builds the system prompt via"
            freeModeRepl -> firewallClient "Screens learner input via"
            freeModeRepl -> sessionFinalizer "Finalizes the session via"
            structuredModeRepl -> memoryManager "Loads and saves learner memory via"
            structuredModeRepl -> promptBuilder "Builds the system prompt via"
            structuredModeRepl -> firewallClient "Screens learner input via"
            structuredModeRepl -> sessionFinalizer "Finalizes the session via"
            structuredModeRepl -> wordPicker "Picks the next focus word via"

            # Web Application -> Tutor Core
            flaskRoutes -> memoryManager "Loads and saves learner memory via"
            flaskRoutes -> promptBuilder "Builds the system prompt via"
            flaskRoutes -> firewallClient "Screens learner input via"
            flaskRoutes -> sessionFinalizer "Finalizes/checkpoints the session via"
            flaskRoutes -> wordPicker "Picks the next focus word via"

            # Tutor Core -> data
            memoryManager -> memoryStore "Reads from and writes to" "File I/O (JSON)"
            wordPicker -> vocabData "Reads the word-frequency list from" "File I/O (CSV, via pandas)"
            sessionFinalizer -> vocabData "Reads CEFR level descriptions from" "File I/O (CSV)"
            promptBuilder -> promptTemplates "Reads the active prompt template from" "File I/O (JSON)"

            # Offline tooling
            contentPipeline -> vocabData "Generates and updates" "Offline batch run by a maintainer"

            # Direct calls to the LLM runtime (both the CLI and the Web Application stream chat completions directly)
            freeModeRepl -> ollama "Streams chat completions from (model: qwen3:8b)" "Ollama Python client"
            structuredModeRepl -> ollama "Streams chat completions from (model: qwen3:8b)" "Ollama Python client"
            flaskRoutes -> ollama "Streams chat completions from (model: qwen3:8b)" "Ollama Python client"
            firewallClient -> ollama "Classifies learner input via (model: prompt-firewall)" "Ollama Python client"
            sessionFinalizer -> ollama "Requests a CEFR session summary from (model: qwen3:8b)" "Ollama Python client"
            modelDefinitions -> ollama "Builds/registers custom models in" "`ollama create` (manual, offline)"
        }

        deploymentEnvironment "Home Network" {
            deploymentNode "Learner's Device" "A phone, tablet or laptop on the home Wi-Fi/LAN." "Any OS" {
                deploymentNode "Web Browser" "" "e.g. Chrome, Safari, Firefox" {
                    chatUiInstance = containerInstance chatUi
                }
            }

            deploymentNode "Tutor Host Machine" "The GPU-equipped machine running the tutor server and local LLM inference." "Linux" {
                deploymentNode "tutor-web process" "Started via the `tutor-web` command" "Flask dev server, 0.0.0.0:5000" {
                    webAppInstance = containerInstance webApp
                }
                deploymentNode "tutor process" "Started via the `tutor` command (optional, same machine)" "Python interpreter" {
                    cliInstance = containerInstance cli
                }
                # Modelled once: the same italian_tutor.tutor module is imported into
                # whichever of the two processes above is running.
                tutorCoreInstance = containerInstance tutorCore
                deploymentNode "Local File System" "" {
                    memoryStoreInstance = containerInstance memoryStore
                    vocabDataInstance = containerInstance vocabData
                    promptTemplatesInstance = containerInstance promptTemplates
                }
                deploymentNode "Ollama Runtime" "Local inference server" "ollama serve" {
                    ollamaInstance = softwareSystemInstance ollama
                }
            }
        }
    }

    views {
        systemContext italianTutor "SystemContext" {
            include *
            autoLayout
            description "The Italian Tutor system in context: a learner uses it, and it depends on a locally-run Ollama LLM server."
        }

        container italianTutor "Containers" {
            include *
            autoLayout
            description "The containers that make up the Italian Tutor: a CLI, a web application and browser UI, a shared core library, local data stores, and offline tooling."
        }

        component cli "CLI_Components" {
            include *
            autoLayout
            description "Components inside the CLI Application, and how they use the shared Tutor Core Library and the Ollama LLM server."
        }

        component webApp "WebApp_Components" {
            include *
            autoLayout
            description "Components inside the Web Application, and how they use the Chat Web UI, the shared Tutor Core Library and the Ollama LLM server."
        }

        component tutorCore "TutorCore_Components" {
            include *
            autoLayout
            description "Components inside the shared Tutor Core Library, and the local data stores / LLM server they depend on."
        }

        dynamic italianTutor "ChatMessageFlow" "Illustrates a single learner chat turn from the web UI, including prompt-injection screening." {
            learner -> chatUi "Types a message and submits the chat form"
            chatUi -> webApp "POST /api/chat { message }"
            webApp -> ollama "Screens the message for prompt injection (model: prompt-firewall)"
            webApp -> ollama "Streams a chat completion (model: qwen3:8b)"
            webApp -> chatUi "Streams Paolo's reply back"
            chatUi -> learner "Renders Paolo's reply"
            autoLayout
        }

        deployment italianTutor "Home Network" "Deployment" {
            include *
            autoLayout
            description "How the containers are deployed across the learner's device and the tutor host machine on a home network."
        }

        styles {
            element "Person" {
                shape person
                background #d35400
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "External System" {
                background #999999
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Browser" {
                shape webBrowser
                background #438dd5
                color #ffffff
            }
            element "Data Store" {
                shape cylinder
                background #85bbf0
                color #000000
            }
            element "Offline Tooling" {
                background #cccccc
                color #000000
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
        }
    }
}
