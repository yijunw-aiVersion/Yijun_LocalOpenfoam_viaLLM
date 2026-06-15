"""Post-processing and visualization."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _latest_vtk_dir(case_dir: Path) -> Path | None:
    vtk_root = Path(case_dir) / "VTK"
    if not vtk_root.exists():
        return None
    time_dirs = sorted([p for p in vtk_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    return time_dirs[-1] if time_dirs else None


def plot_velocity_magnitude(case_dir: Path, output_png: Path) -> Path:
    import pyvista as pv

    vtk_dir = _latest_vtk_dir(case_dir)
    if vtk_dir is None:
        raise FileNotFoundError(f"No VTK output under {case_dir / 'VTK'}")

    vtu_files = list(vtk_dir.glob("*.vtu"))
    if not vtu_files:
        raise FileNotFoundError(f"No .vtu files in {vtk_dir}")

    mesh = pv.read(vtu_files[0])
    if "U" not in mesh.array_names:
        raise KeyError("Vector field U not found in VTK output")

    vectors = mesh.point_data["U"]
    speed = np.linalg.norm(vectors, axis=1)
    mesh.point_data["speed"] = speed

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)

    plotter = pv.Plotter(off_screen=True, window_size=(900, 500))
    plotter.add_mesh(mesh, scalars="speed", cmap="turbo", show_edges=False)
    plotter.view_xy()
    plotter.add_text("Velocity magnitude (m/s)", font_size=10)
    plotter.screenshot(str(output_png))
    plotter.close()
    return output_png


def plot_surface_cp(case_dir: Path, output_png: Path, u_inf: float, rho: float) -> Path:
    import pyvista as pv

    vtk_dir = _latest_vtk_dir(case_dir)
    if vtk_dir is None:
        raise FileNotFoundError(f"No VTK output under {case_dir / 'VTK'}")

    vtp_files = (
        list(vtk_dir.glob("boundary/cylinder.vtp"))
        + list((vtk_dir / "boundary").glob("*.vtp"))
        + list(vtk_dir.glob("*boundary*.vtp"))
    )
    if not vtp_files:
        raise FileNotFoundError(f"No boundary VTP files in {vtk_dir}")

    boundary = pv.read(vtp_files[0])
    if "p" not in boundary.point_data:
        raise KeyError("Pressure field p not found on boundary")

    p = boundary.point_data["p"]
    cp = (p - p.mean()) / (0.5 * rho * u_inf**2)
    pts = boundary.points
    theta = np.arctan2(pts[:, 1], pts[:, 0])
    order = np.argsort(theta)

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(np.degrees(theta[order]), cp[order], "-b", linewidth=1.5)
    ax.set_xlabel("theta (deg)")
    ax.set_ylabel("Cp")
    ax.set_title("Cylinder surface pressure coefficient")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_png, dpi=150)
    plt.close(fig)
    return output_png


def generate_report(case_dir: Path, out_dir: Path, u_inf: float, rho: float) -> dict[str, Path]:
    out_dir = Path(out_dir)
    outputs = {
        "velocity_field": plot_velocity_magnitude(case_dir, out_dir / "velocity_field.png"),
        "surface_pressure": plot_surface_cp(case_dir, out_dir / "surface_pressure.png", u_inf, rho),
    }
    return outputs
