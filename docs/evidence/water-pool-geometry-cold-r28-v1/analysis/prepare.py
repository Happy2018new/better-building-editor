"""Bind the reviewed GUI-coordinate analyzer to the pool-only cold candidate."""
from pathlib import Path

WORK = Path(__file__).resolve().parent
OLD = WORK.with_name('water-formal-analysis-v1')


def main():
    text = (OLD / 'analyze_f_editor.py').read_text(encoding='utf8')
    text = text.replace("HOST = WORK.with_name('water-formal-f-editor-v2')", "HOST = WORK.with_name('water-pool-geometry-cold-v1')")
    target = WORK / 'analyze_pool.py'
    assert not target.exists()
    target.write_text(text, encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
