from pathlib import Path
import os

template = """\
name: Enrich Chunk {chunk_num}

on:
  workflow_dispatch:

jobs:
  enrich-chunk-{chunk_num}:
    runs-on: ubuntu-latest
    env:
      AFFINITY_API_KEY: ${{{{ secrets.AFFINITY_API_KEY }}}}

    steps:
      - name: Checkout repository 
        uses: actions/checkout@v4
        with:
          token: ${{{{ secrets.GH_PAT }}}}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run enrichment for chunk {chunk_num}
        run: python action.py {chunk_num}
      - name: Pull latest changes with rebase
        run: |
          git config user.name "GitHub Actions"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git pull origin main --rebase
      - name: Commit and push changes
        uses: EndBug/add-and-commit@v9
        with:
          author_name: GitHub Actions
          author_email: 41898282+github-actions[bot]@users.noreply.github.com
          message: "Auto-commit enrichment chunk {chunk_num}"
          add: 'enrich_chunk_{chunk_num}.csv'
          push: true
          github_token: ${{{{secrets.GH_PAT}}}}
"""


output_dir = os.path.join(os.getcwd(),".github", "workflows")
os.makedirs(output_dir, exist_ok=True)

# Create files
file_paths = []
for i in range(1, 9):
    content = template.format(chunk_num=i)
    file_path = os.path.join(output_dir, f"run-chunk-{i}.yml")
    with open(file_path, "w") as f:
        f.write(content)
    file_paths.append(file_path)

print("Generated YAML files:")
for path in file_paths:
    print(path)