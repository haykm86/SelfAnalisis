"""Topic alias mapping — canonical_label -> list of raw labels to fold into it.

Review this file before applying. Any raw label NOT listed here keeps its
original value as its canonical_label (i.e. the tail is untouched).

Guidelines used for this draft:
- Fold only labels with a clear shared meaning. When in doubt, keep separate.
- Distinct subtopics stay separate even if they share a prefix
  (e.g. `burnout_recovery` vs `burnout_prevention` — genuinely different).
- Specific technical features stay separate from the general tool
  (e.g. `clickhouse_date_functions` is not folded into `clickhouse`).
- When multiple candidate canonicals exist, prefer the most common raw form.
"""

ALIASES: dict[str, list[str]] = {
    # ---------------- English / language learning ----------------
    "english_learning": [
        "english_learning",
        "english_speaking_practice",
        "english_practice",
        "english_language_learning",
        "english_language",
        "english_fluency",
        "english_conversation_practice",
        "english_vocabulary",
        "english_improvement",
    ],
    "english_grammar": [
        "english_grammar",
        "grammar_correction",
        "grammar_practice",
        "grammar_improvement",
        "grammar_rules",
        "grammar_tenses",
    ],
    "language_learning": [
        "language_learning",
        "language_learning_strategy",
        "language_learning_methods",
        "language_practice",
    ],

    # ---------------- Data structures / algorithms ----------------
    "data_structures_algorithms": [
        "data_structures",
        "data_structures_algorithms",
        "algorithms",
    ],
    "algorithm_complexity": [
        "algorithm_complexity",
        "algorithm_optimization",
        "big_o_notation",
        "time_complexity",
    ],

    # ---------------- .NET / EF Core ----------------
    "entity_framework_core": [
        "entity_framework",
        "entity_framework_core",
        "ef_core",
    ],
    "csharp": [
        "csharp",
        "csharp_programming",
    ],

    # ---------------- Databases ----------------
    "postgresql": [
        "postgresql",
        "postgresql_integration",
    ],
    "clickhouse": [
        "clickhouse",
        "clickhouse_database",
        "clickhouse_client",
        "clickhouse_integration",
        "clickhouse_sql",
    ],
    "database_performance": [
        "database_performance",
        "database_optimization",
    ],
    "performance_optimization": [
        "performance_optimization",
        "performance_tuning",
    ],
    "database_indexes": [
        "database_indexes",
        "index_optimization",
    ],
    "database_migrations": [
        "database_migration",
        "database_migrations",
        "migrations",
    ],

    # ---------------- Microservices / architecture ----------------
    "microservices": [
        "microservices",
        "microservices_architecture",
    ],

    # ---------------- Kafka ----------------
    "kafka": [
        "kafka",
        "apache_kafka",
        "kafka_architecture",
        "kafka_cluster_setup",
    ],
    "kafka_kraft_mode": [
        "kraft_mode",
        "kafka_kraft_mode",
    ],

    # ---------------- Docker ----------------
    "docker": [
        "docker",
        "docker_installation",
        "docker_containerization",
    ],

    # ---------------- Git ----------------
    "git_branching": [
        "git_branching",
        "branch_management",
    ],

    # ---------------- Error / exception handling ----------------
    "error_handling": [
        "error_handling",
        "exception_handling",
    ],

    # ---------------- Interviews / career ----------------
    "interview_preparation": [
        "interview_preparation",
        "job_interview_preparation",
    ],

    # ---------------- Productivity / routines ----------------
    "daily_routines": [
        "daily_routines",
        "daily_routine_description",
        "morning_routine",
    ],

    # ---------------- Project-specific ----------------
    "easypay_integration": [
        "easypay_api_integration",
        "easypay_integration",
    ],
}


def build_reverse_map() -> dict[str, str]:
    """raw_label -> canonical_label. Raises if a raw label appears twice."""
    reverse: dict[str, str] = {}
    for canonical, variants in ALIASES.items():
        for variant in variants:
            if variant in reverse:
                raise ValueError(
                    f"{variant!r} is mapped twice: to {reverse[variant]!r} and {canonical!r}"
                )
            reverse[variant] = canonical
    return reverse


if __name__ == "__main__":
    reverse = build_reverse_map()
    print(f"{len(ALIASES)} canonical labels")
    print(f"{len(reverse)} raw labels covered")
    for canonical in sorted(ALIASES):
        variants = ALIASES[canonical]
        print(f"  {canonical}  <-  {', '.join(v for v in variants if v != canonical)}")
