#!/usr/bin/python3
import math
import os
import sys
import argparse
from pathlib import Path

freecad_paths = [
    '/opt/freecad/usr/lib',
]

for path in freecad_paths:
    if os.path.exists(path):
        sys.path.append(path)

import FreeCAD
import MeshPart

def get_printbed_plane(body):
    """Get the Plane which should be used as the print bed for the body."""
    printbed = None
    flipped = False
    for sub_obj in body.OutList:
        if(sub_obj.TypeId == "App::Origin"):
            for origin in sub_obj.OutList:
                if("printbed" in origin.Label and "Plane" in origin.TypeId):
                    printbed = origin
                    flipped = "flipped" in origin.Label
                    return printbed, flipped
        if("printbed" in sub_obj.Label and "Plane" in sub_obj.TypeId):
            printbed = sub_obj
            flipped = "flipped" in sub_obj.Label
            return printbed, flipped
    raise ValueError("No printbed plane found in part!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export specified bodies from a FreeCAD file to STL.")
    parser.add_argument('cad_file', type=str, help='Path to the FreeCAD file')
    parser.add_argument('parts', type=str, nargs='+', help='List of parts names to export')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory for the STL files')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without exporting STL files')
    args = parser.parse_args()

    message = "Validating" if args.dry_run else "Exporting"
    # Open the FreeCAD file.
    cad_file = Path(args.cad_file)
    doc = FreeCAD.open(str(cad_file.absolute()))

    # Get the parts we want to 3d print.
    parts = {name: None for name in args.parts}

    # Get the parts we want to 3d print.
    export_failed = 0
    for part_name in args.parts:
        try:
            # Find the body in the part.
            print(f"\033[1;36m{message} {part_name}\033[0m")
            part = doc.getObjectsByLabel(part_name)
            assert len(part) == 1, f"Expected exactly 1 part with label '{part_name}' but found {len(part)}"
            assert part[0].TypeId == 'App::Part', f"Expected object with label '{part_name}' to be a Part but was {part[0].TypeId}"
            part = part[0]
            body = [b for b in part.OutList if b.TypeId == "PartDesign::Body"]
            assert len(body) == 1, f"Expected exactly 1 body in part '{part_name}' but found {len(body)}"
            body = body[0]
            print(f" - \033[96mFound body!\033[0m")
            # Get the shape of the body.
            shape = body.Shape.copy(False)
            # Orient the part to the printbed.
            plane, flipped = get_printbed_plane(body)
            matrix = plane.Placement.Matrix.inverse()
            if flipped: # Flip around the printbed plane.
                matrix.rotateX(math.pi)
            shape = shape.transformShape(matrix)
            print(f" - \033[96mReoriented part!\033[0m")
            # Export as .stl file.
            if args.dry_run:
                continue
            print(f" - \033[96mExporting Stl\033[0m")
            mesh = doc.addObject("Mesh::Feature", "Mesh")
            mesh.Mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.01, AngularDeflection=0.025, Relative=False)
            mesh.Mesh.write(f"{args.output_dir}/{part_name}.stl")
        except Exception as e:
            print(f"\033[91mError processing part '{part_name}': {e}\033[0m")
            export_failed = 1

    FreeCAD.closeDocument(doc.Name)

    exit(export_failed)