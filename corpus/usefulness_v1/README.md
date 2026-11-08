# usefulness_v1

12 bounded Python coding tasks (en/zh/ja) with hidden acceptance tests and reference solutions,
plus 6 requests that should produce no code. hidden_tests/ and reference/ are never shown to a generator.
routes/ holds one PacketSpec route contract per route, generated with `rosetta sync` (HUMAN = .md, MACHINE = .cpn).
Success: code tasks pass their hidden tests in the Docker sandbox; no-code tasks produce no code.
