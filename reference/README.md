# reference/ (not tracked)

Reference implementation files from the manager's package, used only to
check the engine against the spec. Confidential: the folder is gitignored.
Drop the `.py` files here (cost_bot_api.py, analogue_estimator.py, onshore_calculator.py, evaluation_harness.py, ...).
`tests/test_calculator_onshore.py` runs a numeric parity check against
`onshore_calculator.py` when it is present and skips otherwise.
`docs/PARITY_cost_bot_api.md` records what was compared and what differs.
