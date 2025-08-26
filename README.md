
# Quantum State Visualizer (Hackathon Prototype)

This project lets you **upload a quantum circuit (QASM)** or build a simple one via a **tiny text DSL**, then simulates it and shows **each qubit's reduced state** on **animated Bloch spheres**.

## ✅ Features
- Upload **.qasm** circuit files (e.g., Bell, GHZ).
- Gate-by-gate **animation** of each qubit's Bloch vector.
- **Partial trace** to show **single-qubit mixed states** from multi-qubit circuits.
- **Color-coded purity**: blue ≈ pure, red = mixed.

## 📁 Project Structure
```
quantum-state-visualizer/
├─ app.py
├─ requirements.txt
└─ samples/
   ├─ bell.qasm
   └─ ghz3.qasm
```

## 🧰 Prerequisites
- Python 3.10+
- VS Code (recommended)
- Windows PowerShell or Terminal

## 🖥️ Setup (Windows PowerShell)
```powershell
# 1) Unzip the project
# 2) Open folder in VS Code (File > Open Folder)

# 3) Create & activate a virtual environment
py -3 -m venv venv
# If activation gives a policy error, run once:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# then close/reopen the terminal.
venv\Scripts\activate

# 4) Install dependencies
pip install -r requirements.txt

# 5) Run the app
streamlit run app.py
```

The browser will open at http://localhost:8501

## 🚀 How to Use
1. Click **"Choose a .qasm file"** and upload one (try `samples/bell.qasm` or `samples/ghz3.qasm`).
2. Or use the **DSL builder** in the sidebar, e.g.:
   ```
   num_qubits 2
   H 0
   CX 0 1
   ```
   Supported gates: `H, X, Y, Z, S, T, RX i θ, RY i θ, RZ i θ, CX c t, CZ a b, SWAP a b`.

3. Toggle **"Animate gate-by-gate"** to see the Bloch vector move step-wise after each gate.

## 📝 Notes
- Animation **stops at measurement** gates if present.
- Max steps can be adjusted in the sidebar to keep it smooth.
- Purity is shown per step for each qubit (Tr(ρ²)).

## 🧠 Why This Is Unique
- Shows **reduced density matrices** per qubit (partial tracing others) to reveal **mixedness from entanglement**.
- Simple IBM-like flow (upload circuit) + clear visuals for judges.

## 🐞 Troubleshooting
- **Policy error when activating venv**: run PowerShell as normal user and execute:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- **Streamlit page not opening**: ensure firewall prompts are accepted, or go to the printed `localhost` URL.
- **QASM parse errors**: ensure file is OpenQASM 2.0 and uses `qelib1.inc` for standard gates.
