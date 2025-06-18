#importing needed packages (install before use)
import vtk
import os
import sys
import logging

# This section sets up logging, logs all levels to a file, and formats log messages
script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'project.log')
logger = logging.getLogger()

# Check if logger already has handlers (to avoid adding multiple handlers)
if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def improve_tin(components,cleaning_tolerance= 0.00025, iterations=10, relaxation=0.1, target_reduction=0.01, artifact_tolerance=50, hole_tolerance=10):
    """
    @brief Optimize a list of TIN meshes by cleaning, decimating, smoothing, and filling holes.

    This function reads each input .vtk file (TIN mesh) and applies a sequence of VTK filters to
    improve mesh quality and remove small artifacts:
      1. vtkCleanPolyData to merge nearly identical points and remove unused points based on the
         specified cleaning_tolerance.
      2. vtkConnectivityFilter to label all connected regions, then discard regions smaller than
         artifact_tolerance cells and reassemble the remaining regions.
      3. vtkDecimatePro to reduce polygon count by target_reduction fraction while preserving the structure.
      4. vtkSmoothPolyDataFilter to perform Laplacian smoothing over the mesh using the given
         iterations and relaxation parameters.
      5. vtkFillHolesFilter to triangulate and close holes defined by hole_tolerance.
      6. vtkPolyDataNormals to recompute and orient normals consistently for the final mesh.

    The optimized mesh is saved as a new “*_optimized.vtk” file in same directory as the input.

    @param components
        A list of file paths to the input TIN meshes (.vtk files).
    @param cleaning_tolerance
        Maximum distance within which points are merged during vtkCleanPolyData (default: 0.00025).
        Increasing this value removes more nearly duplicate points but may alter fine detail.
    @param iterations
        Number of Laplacian smoothing iterations in vtkSmoothPolyDataFilter (default: 10). More
        iterations produce a smoother surface at expense of potential detail loss.
    @param relaxation
        Relaxation factor for Laplacian smoothing (default: 0.1). Higher values allow each vertex to
        move farther toward the average of its neighbors during each smoothing iteration.
    @param target_reduction
        Fraction of polygons to remove in vtkDecimatePro (default: 0.01).
        Larger values yield more aggressive decimation.
    @param artifact_tolerance
        Minimum number of cells in a connected region to retain (default: 50). Any region with fewer
        cells than this threshold is discarded as an artifact.
    @param hole_tolerance
        Maximum approximative radius of holes to fill in vtkFillHolesFilter (default: 10). Only
        holes smaller than this value will be closed; larger holes remain open.

    @return
        None. For each input mesh, a corresponding “<basename>_optimized.vtk” file is written.
        Progress messages and errors are printed to stderr. Nothing is downstreamed via stdout anymore
        since this is the final script of the system.

    @exception RuntimeError
        If any step fails (reading, filtering, or writing), an error is written to stderr and the
        program terminates immediately.
    """
    logger.info(" ")
    logger.info("**MESH OPTIMIZATION**" + "\n")
    logger.info(" ")

    # Loop through each component and apply the optimization process
    for component in components:
        try:
            # Read VTK file using PolyData reader
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(component)  # Set the filename of mesh
            reader.Update()  # Update reader to read data
            poly_data = reader.GetOutput()  # Get output polydata (mesh)

            # The following stages apply filters and optimization steps to mesh
            # Clean the mesh
            clean_filter = vtk.vtkCleanPolyData()
            clean_filter.SetInputData(poly_data)
            clean_filter.SetTolerance(cleaning_tolerance)
            clean_filter.PointMergingOn()
            clean_filter.Update()

            # Apply connectivity filter to remove artifacts
            connectivity_filter = vtk.vtkConnectivityFilter()
            connectivity_filter.SetInputData(clean_filter.GetOutput())
            connectivity_filter.SetExtractionModeToAllRegions()
            connectivity_filter.ColorRegionsOn()
            connectivity_filter.Update()

            num_regions = connectivity_filter.GetNumberOfExtractedRegions()
            append_filter = vtk.vtkAppendPolyData()

            for region_id in range(num_regions):
                # Extract only specified region
                region_filter = vtk.vtkConnectivityFilter()
                region_filter.SetInputData(clean_filter.GetOutput())
                region_filter.SetExtractionModeToSpecifiedRegions()
                region_filter.InitializeSpecifiedRegionList()
                region_filter.AddSpecifiedRegion(region_id)
                region_filter.Update()

                region_output = region_filter.GetOutput()
                num_cells = region_output.GetNumberOfCells()

                if num_cells >= artifact_tolerance:  # Minimum cell count to keep
                    append_filter.AddInputData(region_output)

            # Combine retained regions
            append_filter.Update()

            # Decimate mesh by reducing size
            decimate = vtk.vtkDecimatePro()
            decimate.SetInputData(append_filter.GetOutput())
            decimate.SetTargetReduction(target_reduction)
            decimate.PreserveTopologyOn()
            decimate.Update()

            # Apply Laplacian smoothing to the mesh
            smoother = vtk.vtkSmoothPolyDataFilter()
            smoother.SetInputData(decimate.GetOutput())
            smoother.SetNumberOfIterations(iterations)
            smoother.SetRelaxationFactor(relaxation)
            smoother.FeatureEdgeSmoothingOff()
            smoother.Update()

            # Create the hole-filling filter
            fill_holes_filter = vtk.vtkFillHolesFilter()
            fill_holes_filter.SetInputData(smoother.GetOutput())
            fill_holes_filter.SetHoleSize(hole_tolerance)
            fill_holes_filter.Update()

            # Retrieve the output with holes filled
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(fill_holes_filter.GetOutput())
            normals.ConsistencyOn()
            normals.AutoOrientNormalsOn()
            normals.SplittingOff()
            normals.Update()

        except Exception as e:
            # If an error occurs, log it and terminate program
            logger.critical("TIN mesh could not be optimized for: " + os.path.basename(component) + ". CTA Model Framework is terminating",exc_info=e)
            sys.exit(1)

        try:
            # Write optimized mesh to a new VTK file
            writer = vtk.vtkPolyDataWriter()
            writer.SetFileName(os.path.join(os.path.dirname(component), f"{os.path.splitext(os.path.basename(component))[0]}_optimized.vtk"))
            writer.SetInputData(normals.GetOutput())  # Set final output mesh for writing
            writer.Write()  # Write mesh to the file
            logger.info("Optimized TIN successfully saved for " + os.path.basename(component))

        except Exception as e:
            # If an error occurs during saving, log it and terminate the program
            logger.critical("Optimized TIN mesh could not be written to: " + os.path.basename(component) + ". CTA Model Framework is terminating",exc_info=e)
            sys.exit(1)

    # Final message indicating completion of all optimization steps
    logger.info("All steps finished. vtk-TIN files can be found in the specified location \n")

# Read input list of components (mesh files) from stdin
components = [line.strip() for line in sys.stdin]



# Read the command-line arguments for optimization parameters
cleaning_tolerance = float(sys.argv[1])
relaxation = float(sys.argv[2])
iterations = int(sys.argv[3])
artifact_tolerance = int(sys.argv[4])
target_reduction = float(sys.argv[5])
hole_tolerance = int(sys.argv[6])

if len(components) >=1:
    improve_tin(components,cleaning_tolerance, iterations, relaxation,
            target_reduction, artifact_tolerance, hole_tolerance)
