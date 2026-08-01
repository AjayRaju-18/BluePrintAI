# demo_data/

Seeded example drawings for instant demo loading (no live API call required).

Each example consists of a pair of files:

| File | Purpose |
|---|---|
| `drawing_<name>.png` | Raster image of the engineering drawing |
| `drawing_<name>.json` | Pre-computed `ExtractedDrawingData` JSON |
| `manifest.json` | Index of all examples (id, label, tags, file paths) |

## Examples included

| id | Part | Material | Key GD&T |
|---|---|---|---|
| `bracket` | Mounting Bracket | Al 6061-T6 | Flatness, Perpendicularity |
| `shaft` | Drive Shaft | SS 304 | Cylindricity, Runout, True Position |
| `flange` | Flange Plate | MS A36 | True Position (bolt pattern), Flatness |

## Adding new seeded examples

1. Place a PNG/JPEG image here named `drawing_<id>.png`.
2. Create a matching `drawing_<id>.json` following the schema in
   `../../shared/extracted_drawing_data.schema.json`.
3. Add an entry to `manifest.json`.
4. The backend `/api/demo` router will pick it up automatically.
