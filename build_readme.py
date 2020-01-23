#!/usr/bin/env python
# Read in our template
template = open("./readme_data/readme_template.md", "r").read()

# Read in our schemas
report = open("./readme_data/schemas/report_schema.jsonc", "r").read().strip()
profile = open("./readme_data/schemas/profile_schema.jsonc", "r").read().strip()
control = open("./readme_data/schemas/control_schema.jsonc", "r").read().strip()

# Format
readme = template.format(report_schema=report, profile_schema=profile, control_schema=control)

# Write
open("./README.md", "w").write(readme)
