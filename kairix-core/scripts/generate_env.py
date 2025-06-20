REQUIRED_VARS = (True,
    "Kairix", [
        "KAIRIX_AGENT_CONFIG_SET",
        "NEO4J_URL",
        "KAIRIX_USER_NAME",
        "KAIRIX_PERSONA_NAME",
        "KAIRIX_N_SUMMARIES_PER_MESSAGE",
    ]
)

OPTIONAL_VARS = (False,
    "Kairix Opt",
    [
        "OPENAI_API_KEY",
        "KAIRIX_SUMMARIZER_ENABLE_QUANTIZATION"
        "KAIRIX_DEBUG"
        "ELEVENLABS_API_KEY"
    ]
)

OLLAMA_VARS = (False,
    "Ollama", [
        "OLLAMA_DEBUG",
        "OLLAMA_KEEP_ALIVE",
        "OLLAMA_MAX_LOADED_MODELS",
        "OLLAMA_MAX_QUEUE",
        "OLLAMA_NUM_PARALLEL",
        "OLLAMA_NOPRUNE",
        "OLLAMA_SCHED_SPREAD",
        "OLLAMA_FLASH_ATTENTION",
        "OLLAMA_KV_CACHE_TYPE",
        "OLLAMA_GPU_OVERHEAD",
        "OLLAMA_HOST"
    ]
)


OUTPUT_DIRS = [
    ("kairix-offline", lambda f: f"../kairix-offline/env/{f}.env"),
    ("kairix-apps", lambda f: f"../kairix-apps/env/{f}.env")
]


VAR_SETS = [REQUIRED_VARS, OPTIONAL_VARS, OLLAMA_VARS]


def format_line(var, val):
    return f"{var}={val}\n"

def gen_set(lines, is_required, var_set, name):
    for v in var_set:
        if is_required or input(f"[{name}] Config optional var ({v})? (y/n)"):
            x = input(f"Value for required var ({v}):\t")
            assert x and x.strip() != ''
        lines.append(format_line(v, x))

def do():
    lines = []

    for is_required, name, vars in VAR_SETS:
        if is_required or 'y' == input("Config optional vars? (y/n)"):
            gen_set(lines, is_required, name, vars)

    file_name = input("Enter file name (*.env): ")

    for name, path_template in OUTPUT_DIRS:
        if "y" == input("Generate for {name? (y/n)"):
            with open(path_template(file_name), "w") as f:
                f.writelines(lines)
                print("Written.")



if __name__ == "__main__":
    do()
