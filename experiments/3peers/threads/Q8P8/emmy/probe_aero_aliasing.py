"""Probe observation aliasing and finite-difference object influence in Aero MuJoCo."""

from __future__ import annotations

import argparse
from pathlib import Path

import mujoco
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import brentq


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.scene))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    print(f"nq={model.nq} nv={model.nv} nu={model.nu} nsensor={model.nsensor} nbody={model.nbody}")
    for kind, count in ((mujoco.mjtObj.mjOBJ_BODY, model.nbody), (mujoco.mjtObj.mjOBJ_JOINT, model.njnt), (mujoco.mjtObj.mjOBJ_ACTUATOR, model.nu), (mujoco.mjtObj.mjOBJ_SENSOR, model.nsensor)):
        label = str(kind).split(".")[-1]
        print(label, [mujoco.mj_id2name(model, kind, i) for i in range(count)])
    print("qpos", data.qpos)
    print("ctrlrange", model.actuator_ctrlrange)
    print("sensordata", data.sensordata)

    # The equality constraints tie PIP/DIP and thumb MCP/IP. Parameterize only
    # configurations satisfying those constraints.
    def expand(x: np.ndarray) -> np.ndarray:
        q = np.zeros(16)
        for finger in range(4):
            q[3 * finger] = x[2 * finger]
            q[3 * finger + 1 : 3 * finger + 3] = x[2 * finger + 1]
        q[12] = x[8]
        q[13] = x[9]
        q[14:16] = x[10]
        return q

    def observe(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        data.qpos[:] = expand(x)
        mujoco.mj_forward(model, data)
        tips = data.xpos[[6, 10, 14, 18, 22]].copy().ravel()
        return data.sensordata.copy(), tips

    x0 = np.array([0.55, 0.45] * 4 + [0.55, 0.45, 0.45])
    y0, p0 = observe(x0)
    eps = 1e-5
    js = np.column_stack([(observe(x0 + eps * np.eye(11)[i])[0] - y0) / eps for i in range(11)])
    jp = np.column_stack([(observe(x0 + eps * np.eye(11)[i])[1] - p0) / eps for i in range(11)])
    null = null_space(js)
    _, _, vh = np.linalg.svd(jp @ null, full_matrices=False)
    direction = null @ vh[0]
    direction /= np.max(np.abs(direction))
    print(f"sensor_jacobian_rank={np.linalg.matrix_rank(js)} nullity={null.shape[1]}")
    print("phase-matched paired states (same fixed wrist):")
    for delta in (0.02, 0.05, 0.10):
        ya, pa = observe(x0 - delta * direction)
        yb, pb = observe(x0 + delta * direction)
        print(
            f"delta={delta:.3f} max_encoder_difference={np.max(np.abs(ya-yb)):.9g} "
            f"max_tip_displacement={np.max(np.linalg.norm((pa-pb).reshape(5, 3), axis=1)):.9g}"
        )
    print("x_minus", x0 - 0.1 * direction)
    print("x_plus", x0 + 0.1 * direction)

    # Exact construction for the pinky: change MCP angle and solve its coupled
    # distal angle so that the measured tendon length is exactly the baseline.
    target = y0[3]
    exact = []
    for mcp in (0.45, 0.65):
        def residual(distal: float) -> float:
            x = x0.copy()
            x[6:8] = (mcp, distal)
            return observe(x)[0][3] - target

        distal = brentq(residual, 0.1, 0.8)
        x = x0.copy()
        x[6:8] = (mcp, distal)
        exact.append((x, *observe(x)))
    xa, ya, pa = exact[0]
    xb, yb, pb = exact[1]
    print("exact paired states:")
    print(f"max_encoder_difference={np.max(np.abs(ya-yb)):.12g}")
    print(f"max_tip_displacement={np.max(np.linalg.norm((pa-pb).reshape(5, 3), axis=1)):.12g}")
    print("x_a", xa)
    print("x_b", xb)


if __name__ == "__main__":
    main()
