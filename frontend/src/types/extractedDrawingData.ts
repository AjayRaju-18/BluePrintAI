/**
 * TypeScript interfaces mirroring shared/extracted_drawing_data.schema.json
 *
 * Source of truth: /shared/extracted_drawing_data.schema.json
 * All bbox arrays are [x, y, w, h] normalized to [0, 1] relative to image size.
 */

/** Normalized bounding box: [x, y, width, height] all in [0, 1] */
export type BBox = [number, number, number, number];

/** A single dimensional annotation on the drawing */
export interface Dimension {
  /** Nominal dimension value, e.g. "25.4" */
  value: string;
  /** Tolerance string, e.g. "±0.05" or "REF" */
  tolerance: string;
  bbox: BBox;
}

/** A GD&T feature control frame annotation */
export interface GDTCallout {
  /** GD&T characteristic name, e.g. "flatness", "true position" */
  characteristic: string;
  /** Tolerance zone value, e.g. "0.05" or "Ø0.1 M" */
  tolerance_zone: string;
  /** Referenced datums as a string, e.g. "A|B|C" or "" */
  datum_refs: string;
  bbox: BBox;
}

/** A surface finish / roughness annotation */
export interface SurfaceFinish {
  /** Surface roughness value, e.g. "Ra 1.6" or "63 μin" */
  value: string;
  bbox: BBox;
}

/** Complete extraction result for one engineering drawing */
export interface ExtractedDrawingData {
  /** Name or identifier of the part */
  part_name: string;
  /** Material specification, e.g. "Al 6061-T6" */
  material: string;
  /** Drawing scale, e.g. "1:1" or "NTS" */
  scale: string;
  /** Drawing revision identifier, e.g. "A" or "01" */
  revision: string;
  /** Required quantity, e.g. "1" or "AS REQ" */
  quantity: string;
  dimensions: Dimension[];
  gdt_callouts: GDTCallout[];
  surface_finish: SurfaceFinish[];
  /** General notes from the title block or note field */
  notes: string[];
}
