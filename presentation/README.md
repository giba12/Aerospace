# Presentation materials

| File | What it is |
|---|---|
| `sensor-sim-linkedin-carousel.pdf` | 16-page 4:5 portrait document for LinkedIn (upload as a document post). Vector, 1080 x 1350 px pages. |
| `sensor-sim-slides.pptx` | 20-slide 16:9 deck with speaker notes. Text and shapes are editable; charts and SysML diagrams are images. |
| `PROJECT_SUMMARY.md` | Project summary under 2,000 characters. |
| `src/` | The builders. Every number is read from the repository (`out/run.csv`, `docs/VALIDATION.md`, `docs/requirements.csv`, the test sources). |

Rebuild (needs `python-pptx` and `matplotlib` 3.10; run `./run.sh` first so `out/run.csv` exists):

```bash
python3 presentation/src/build_carousel.py
python3 presentation/src/build_deck.py
```

This is an educational simulation, not flight software.
