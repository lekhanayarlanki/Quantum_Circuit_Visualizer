import io
import streamlit as st
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix, partial_trace, Statevector
import numpy as np
import plotly.graph_objects as go
from openai import OpenAI
import os

# ================== Predefined Quantum Q&A ==================
qa_dict = {
    "what is a qubit": "A qubit is the basic unit of quantum information, like a classical bit but it can exist in a superposition of |0> and |1>.",
    "what is superposition": "Superposition allows a qubit to be in multiple states at once, like both 0 and 1 simultaneously.",
    "what is entanglement": "Entanglement is when qubits are correlated so that measuring one affects the other, no matter the distance.",
    "what is a quantum gate": "A quantum gate is an operation that changes the state of qubits, similar to logic gates in classical computing.",
    "what is measurement": "Measurement collapses a qubit's superposition into a definite state, either |0> or |1>.",
    "how to create a bell state": "Apply a Hadamard gate to qubit 0, then a CNOT gate with control 0 and target 1.",
    "what is a density matrix": "A density matrix represents the state of a quantum system, especially useful for mixed states.",
    "what is a bloch sphere": "A Bloch sphere is a 3D representation of a single qubit's state, showing superposition and phase.",
    "what is decoherence": "Decoherence is the loss of quantum information due to interaction with the environment, causing superposition to collapse.",
    "what is quantum circuit": "A quantum circuit is a sequence of quantum gates applied to qubits to perform computations."
}


st.set_page_config(page_title="Quantum State Visualizer", layout="wide")

# ============ UI Header ============
st.title("🌀 Quantum State Visualizer")
st.caption("Upload a QASM circuit, simulate it, and see each qubit's reduced state on animated Bloch spheres.")

# Sidebar options
with st.sidebar:
    st.header("Controls")
    animate = st.toggle("Animate gate-by-gate", value=True, help="Animate Bloch vector over gates.")
    max_steps = st.slider("Max gates to animate", 1, 50, 25, help="Limit animation length for performance.")
    st.markdown("---")
    st.subheader("Build (Optional Quick DSL)")
    st.write("You can build a small circuit using a simple text DSL. Example below.")
    dsl_example = "num_qubits 2\nH 0\nCX 0 1"
    dsl_text = st.text_area("Circuit DSL", value=dsl_example, height=150)
    build_btn = st.button("Build circuit from DSL")


# ============ Helpers ============
X = np.array([[0, 1],[1, 0]], dtype=complex)
Y = np.array([[0, -1j],[1j, 0]], dtype=complex)
Z = np.array([[1, 0],[0, -1]], dtype=complex)
PAULI = (X, Y, Z)

def purity(rho_1q: np.ndarray) -> float:
    return float(np.real(np.trace(rho_1q @ rho_1q)))

def bloch_vec(rho_1q: np.ndarray):
    # Expectation values of X, Y, Z for 1-qubit density matrix
    return np.array([float(np.real(np.trace(rho_1q @ P))) for P in PAULI])

def qc_from_dsl(text: str) -> QuantumCircuit:
    """
    Very small DSL for quick prototypes:
      num_qubits N
      H i | X i | Y i | Z i | S i | T i
      RX i theta | RY i theta | RZ i theta   (theta in radians)
      CX c t | CZ a b | SWAP a b
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines or not lines[0].lower().startswith("num_qubits"):
        raise ValueError("First line must be like: num_qubits 2")
    parts = lines[0].split()
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError("num_qubits line must be: num_qubits N")
    nq = int(parts[1])
    qc = QuantumCircuit(nq)
    for ln in lines[1:]:
        toks = ln.split()
        gate = toks[0].upper()
        if gate in {"H","X","Y","Z","S","T"}:
            if len(toks)!=2: raise ValueError(f"{gate} requires 1 index")
            i = int(toks[1]); getattr(qc, gate.lower())(i)
        elif gate in {"RX","RY","RZ"}:
            if len(toks)!=3: raise ValueError(f"{gate} requires index and angle")
            i = int(toks[1]); theta = float(toks[2])
            getattr(qc, gate.lower())(theta, i)
        elif gate=="CX":
            if len(toks)!=3: raise ValueError("CX requires control and target")
            c = int(toks[1]); t = int(toks[2]); qc.cx(c, t)
        elif gate=="CZ":
            if len(toks)!=3: raise ValueError("CZ requires two indices")
            a = int(toks[1]); b = int(toks[2]); qc.cz(a, b)
        elif gate=="SWAP":
            if len(toks)!=3: raise ValueError("SWAP requires two indices")
            a = int(toks[1]); b = int(toks[2]); qc.swap(a, b)
        else:
            raise ValueError(f"Unknown instruction: {ln}")
    return qc

def states_after_each_gate(qc: QuantumCircuit, step_limit=None):
    """
    Returns a list of (k, DensityMatrix) for k=0..K where k indexes gates applied.
    k=0 is the initial |0...0>.
    Stops before measurement; ignores barriers.
    """
    states = []
    working = QuantumCircuit(qc.num_qubits)
    states.append((0, DensityMatrix.from_instruction(working)))
    count = 0
    for inst, qargs, cargs in qc.data:
        name = inst.name
        if name in {"barrier"}:
            continue
        if name in {"measure"}:
            break  # stop animation at measurement
        working.append(
    inst,
    [working.find_bit(q).index for q in qargs],
    [working.find_bit(c).index for c in cargs]
)

        count += 1
        states.append((count, DensityMatrix.from_instruction(working)))
        if step_limit is not None and count >= step_limit:
            break
    return states

def bloch_vectors_per_qubit(states, num_qubits: int):
    """
    For each qubit i, returns a list of dicts per step: 
      {"vec": np.array([x,y,z]), "purity": float}
    """
    from qiskit.quantum_info import partial_trace
    per_qubit = {i: [] for i in range(num_qubits)}
    for step, rho_full in states:
        for i in range(num_qubits):
            keep = [i]
            red = partial_trace(rho_full, [j for j in range(num_qubits) if j not in keep])
            rho_i = red.data if hasattr(red, "data") else np.array(red)
            vec = bloch_vec(rho_i)
            per_qubit[i].append({"vec": vec, "purity": purity(rho_i)})
    return per_qubit

def bloch_sphere_figure(frames_vecs, title="Qubit", show_animation=True):
    """
    frames_vecs: list of dicts with 'vec' and 'purity' for each step.
    Returns a Plotly Figure with a unit sphere, axes, and an arrow (line + cone) that animates.
    """
    # Base sphere
    phi = np.linspace(0, np.pi, 40)
    theta = np.linspace(0, 2*np.pi, 40)
    x = np.outer(np.sin(phi), np.cos(theta))
    y = np.outer(np.sin(phi), np.sin(theta))
    z = np.outer(np.cos(phi), np.ones_like(theta))

    # initial vector
    v0 = frames_vecs[0]["vec"]
    pur0 = frames_vecs[0]["purity"]
    color0 = "blue" if pur0 > 0.99 else "red"

    sphere = go.Surface(x=x, y=y, z=z, opacity=0.15, showscale=False)
    # axes
    axis_len = 1.2
    axes = [
        go.Scatter3d(x=[-axis_len, axis_len], y=[0,0], z=[0,0], mode="lines", name="X", line=dict(width=2)),
        go.Scatter3d(x=[0,0], y=[-axis_len, axis_len], z=[0,0], mode="lines", name="Y", line=dict(width=2)),
        go.Scatter3d(x=[0,0], y=[0,0], z=[-axis_len, axis_len], mode="lines", name="Z", line=dict(width=2)),
    ]

    # arrow (line + cone)
    line = go.Scatter3d(
        x=[0, v0[0]], y=[0, v0[1]], z=[0, v0[2]],
        mode="lines+markers",
        marker=dict(size=3),
        line=dict(width=8, color=color0),
        name="Bloch vector"
    )
    cone = go.Cone(
        x=[0], y=[0], z=[0],
        u=[v0[0]], v=[v0[1]], w=[v0[2]],
        anchor="tail", sizemode="absolute", sizeref=0.4,
        showscale=False, colorscale=[[0, color0],[1, color0]],
        name=""
    )

    data = [sphere] + axes + [line, cone]

    layout = go.Layout(
    title=title,
    scene=dict(
        xaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False),
        yaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False),
        zaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False),
        aspectmode="cube"
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    width=500,   # force square figure
    height=500,  # same as width
)

       

    if show_animation and len(frames_vecs) > 1:
        frames = []
        for f in frames_vecs:
            v = f["vec"]; pur = f["purity"]
            col = "blue" if pur > 0.99 else "red"
            frames.append(go.Frame(data=[
                sphere, *axes,
                go.Scatter3d(x=[0, v[0]], y=[0, v[1]], z=[0, v[2]], mode="lines+markers",
                             marker=dict(size=3),
                             line=dict(width=8, color=col)),
                go.Cone(x=[0], y=[0], z=[0], u=[v[0]], v=[v[1]], w=[v[2]],
                        anchor="tail", sizemode="absolute", sizeref=0.4,
                        showscale=False, colorscale=[[0, col],[1, col]])
            ]))
        layout.updatemenus = [dict(type="buttons",
                                   buttons=[dict(label="Play", method="animate", args=[None, {"frame": {"duration": 600, "redraw": True}, "fromcurrent": True}]),
                                            dict(label="Pause", method="animate", args=[[None], {"mode": "immediate"}])],
                                   showactive=False)]
        fig = go.Figure(data=data, layout=layout, frames=frames)
    else:
        fig = go.Figure(data=data, layout=layout)
    return fig

def render_circuit_summary(qc: QuantumCircuit):
    st.subheader("🧩 Circuit Summary")
    st.write(f"- **Qubits:** {qc.num_qubits}")
    st.write(f"- **Gates:** {len(qc.data)} (animation stops at measurement)")
    st.code(qc.draw(output='text', fold=200).__str__())


# ============ Main Panels ============
left, right = st.columns([1, 2])

with left:
    st.subheader("⬆️ Upload QASM")
    file = st.file_uploader("Choose a .qasm file", type=["qasm"])

    qc = None
    if file is not None:
        try:
            qasm_str = file.getvalue().decode("utf-8")
            qc = QuantumCircuit.from_qasm_str(qasm_str)
            st.success("QASM loaded successfully.")
        except Exception as e:
            st.error(f"Failed to parse QASM: {e}")

    st.markdown("---")
    if build_btn:
        try:
            qc = qc_from_dsl(dsl_text)
            st.success("Circuit built from DSL.")
        except Exception as e:
            st.error(f"DSL error: {e}")

    # --- Chatbot directly under DSL build button ---
    st.markdown("---")
    st.subheader("💬 Quantum Study Assistant")
    user_question = st.text_input("Ask me anything about quantum circuits, qubits, or the visualizer:")

    if user_question:
        question = user_question.strip().lower()  # convert to lowercase
        answer = qa_dict.get(question, "Sorry, I don't have an answer for that yet. Try asking something else or check the documentation.")
        st.success("🤖 Assistant says:")
        st.write(answer)



with right:
    if qc is None:
        st.info("Upload a QASM file or build with the DSL to begin. Examples: Bell (2 qubits), GHZ (3 qubits).")
    else:
        render_circuit_summary(qc)

        # Compute states and Bloch data
        states = states_after_each_gate(qc, step_limit=(max_steps if animate else None))
        per_qubit = bloch_vectors_per_qubit(states, qc.num_qubits)

        st.subheader("🔭 Bloch Spheres")
        cols = st.columns(qc.num_qubits if qc.num_qubits>0 else 1)
        for i in range(qc.num_qubits):
            frames_vecs = per_qubit[i]
            fig = bloch_sphere_figure(frames_vecs, title=f"Qubit {i}", show_animation=animate)
            fig.update_layout(
                height=540,                       # height in px (adjust if you want bigger/smaller)
        margin=dict(l=0, r=0, t=30, b=0),
        scene=dict(
            xaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False, visible=False),
            yaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False, visible=False),
            zaxis=dict(range=[-1.2, 1.2], zeroline=False, showgrid=False, visible=False),
            aspectmode="cube"
        )
    )
            cols[i].plotly_chart(fig, use_container_width=True)
            
     

        # Purity table
        st.subheader("📈 Purity by step")
        for i in range(qc.num_qubits):
            purities = [f"{f['purity']:.3f}" for f in per_qubit[i]]
            st.write(f"Qubit {i}: " + " → ".join(purities))

st.markdown("---")
st.caption("Tip: Arrow color — **blue** = near-pure, **red** = mixed (entanglement/noise). Animation shows state after each gate.")


