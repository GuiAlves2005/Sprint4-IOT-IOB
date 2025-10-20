import cv2
import dlib
import numpy as np
import sqlite3
import json
import os
import time
import serial


# CONFIGURAÇÕES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


PREDICTOR_PATH = os.path.join(BASE_DIR, "shape_predictor_5_face_landmarks.dat")
RECOG_MODEL_PATH = os.path.join(BASE_DIR, "dlib_face_recognition_resnet_model_v1.dat")
DB_FILE = os.path.join(BASE_DIR, "faces.db")

RESIZE_FACTOR = 0.5
PROCESS_EVERY_N_FRAMES = 5
RECOGNITION_THRESHOLD = 0.5 

SERIAL_PORT = "COM7"   
SERIAL_BAUD = 9600

WELCOME_MESSAGES = {
    "Conservador": "Bem-vindo, investidor conservador! Foco em segurança.",
    "Moderado":    "Bem-vindo, investidor moderado! Equilíbrio risco-retorno.",
    "Agressivo":   "Bem-vindo, investidor agressivo! Oportunidades de alto risco."
}

OPEN_RELAY_PAYLOAD = b"OPEN\n" 


# BANCO (SQLite)

def get_db():
    """Abre/cria o banco e garante a tabela de usuários."""
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            profile TEXT NOT NULL,
            descriptor TEXT NOT NULL,  -- JSON do vetor (128 floats)
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    return con

def list_users(con):
    cur = con.execute("SELECT id, name, profile, created_at FROM users ORDER BY id;")
    return cur.fetchall()

def insert_user(con, name, profile, descriptor):
    """Insere um usuário (descriptor deve ser list ou np.ndarray)."""
    if isinstance(descriptor, np.ndarray):
        descriptor = descriptor.tolist()
    con.execute(
        "INSERT INTO users (name, profile, descriptor) VALUES (?, ?, ?);",
        (name.strip(), profile, json.dumps(descriptor))
    )
    con.commit()

def load_all_descriptors(con):
    """Carrega (id, name, profile, vetor_numpy) de todos os usuários."""
    cur = con.execute("SELECT id, name, profile, descriptor FROM users;")
    rows = cur.fetchall()
    users = []
    for uid, name, profile, desc_json in rows:
        vec = np.array(json.loads(desc_json), dtype=np.float32)
        users.append((uid, name, profile, vec))
    return users

# ---- Sessão do app ----
def ensure_session_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS app_session (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            user_id INTEGER,
            user_name TEXT,
            started_at DATETIME
        );
    """)
   
    con.execute("INSERT OR IGNORE INTO app_session (id, user_id, user_name, started_at) VALUES (1, NULL, NULL, NULL);")
    con.commit()

def set_session(con, user_id: int, user_name: str):
    con.execute(
        "UPDATE app_session SET user_id=?, user_name=?, started_at=CURRENT_TIMESTAMP WHERE id=1;",
        (user_id, user_name)
    )
    con.commit()

def clear_session(con):
    con.execute("UPDATE app_session SET user_id=NULL, user_name=NULL, started_at=NULL WHERE id=1;")
    con.commit()


# MODELOS dlib 

def ensure_file(path, label):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Arquivo '{label}' não encontrado em: {path}\n"
            f"Coloque o arquivo correto (.dat) nessa pasta."
        )
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb < 1:  
        raise RuntimeError(
            f"O arquivo '{label}' parece inválido (tamanho muito pequeno: {size_mb:.2f} MB).\n"
            f"Baixe novamente o .dat oficial."
        )

ensure_file(PREDICTOR_PATH, "shape_predictor_5_face_landmarks.dat")
ensure_file(RECOG_MODEL_PATH, "dlib_face_recognition_resnet_model_v1.dat")

detector = dlib.get_frontal_face_detector()
shape_predictor = dlib.shape_predictor(PREDICTOR_PATH)
face_recognizer = dlib.face_recognition_model_v1(RECOG_MODEL_PATH)

def compute_descriptor(rgb_img, rect):
    """Retorna vetor facial (128,) em float32 dado um retângulo no frame."""
    shape = shape_predictor(rgb_img, rect)
    desc = face_recognizer.compute_face_descriptor(rgb_img, shape)
    return np.array(desc, dtype=np.float32)

def euclidean(a, b):
    d = a - b
    return float(np.sqrt((d * d).sum()))


# SERIAL 

def try_open_serial(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
        time.sleep(2)
        print(f"[INFO] Porta serial {port} conectada.")
        return ser
    except Exception as e:
        print(f"[WARN] Serial não conectada ({e}). Seguindo sem serial.")
        return None


# FLUXO PRINCIPAL

def main():
    # Banco
    con = get_db()
    ensure_session_table(con)
    clear_session(con)  

    print("\n--- Usuários cadastrados ---")
    for row in list_users(con):
        print(row)

    # Serial 
    ser = try_open_serial(SERIAL_PORT, SERIAL_BAUD)

    # Câmera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERRO] Não conseguiu abrir a câmera.")
        return

    print("\n--- Comandos ---")
    print("[V] alterna validação ON/OFF")
    print("[C] cadastra o rosto visível (se houver 1 rosto)")
    print("[Q] sair\n")

    validando = True
    frame_count = 0

 
    last_faces = []         
    last_descriptor = None   

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_count += 1

        # pré-processamento 
        small = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # processar somente a cada N frames
        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            last_faces = []
            rects = detector(rgb_small, 0)  

            users_cache = load_all_descriptors(con) if validando else []

            for r in rects:
                desc = compute_descriptor(rgb_small, r)
                last_descriptor = desc  # para cadastro

                name, profile, best_dist = "Desconhecido", "", 999.0
                matched_user_id = None

                if validando and users_cache:
                    for uid, uname, uprof, uvec in users_cache:
                        d = euclidean(desc, uvec)
                        if d < best_dist:
                            name, profile, best_dist = uname, uprof, d
                            matched_user_id = uid

                    if best_dist > RECOGNITION_THRESHOLD:
                        name, profile = "Desconhecido", ""
                        matched_user_id = None

                # Se reconheceu, grava a sessão para o app web
                if name != "Desconhecido" and matched_user_id is not None:
                    set_session(con, matched_user_id, name)

                last_faces.append((r, name, profile, best_dist))

        # desenha com base no último cálculo
        h, w = frame.shape[:2]
        for r, name, profile, dist in last_faces:
            top = int(r.top() / RESIZE_FACTOR)
            right = int(r.right() / RESIZE_FACTOR)
            bottom = int(r.bottom() / RESIZE_FACTOR)
            left = int(r.left() / RESIZE_FACTOR)

            color = (0, 200, 0) if name != "Desconhecido" else (0, 0, 200)
            label = f"{name}" + (f" ({profile})" if profile else "")
            if name != "Desconhecido":
                label += f"  d={dist:.3f}"

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, label, (left, max(25, top - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if name != "Desconhecido":
                msg = WELCOME_MESSAGES.get(profile, "Acesso liberado.")
                cv2.putText(frame, msg, (10, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 200, 255), 2)
                # aciona serial uma vez por detecção
                if ser:
                    try:
                        ser.write(OPEN_RELAY_PAYLOAD)
                    except Exception:
                        pass
            else:
                cv2.putText(frame, "Nao reconhecido. Pressione C para cadastrar.",
                            (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 255), 2)

        status = f"Validacao: {'ON' if validando else 'OFF'}  (threshold={RECOGNITION_THRESHOLD})"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 200, 0) if validando else (0, 0, 200), 2)

        cv2.imshow("Reconhecimento Facial", frame)
        k = cv2.waitKey(1) & 0xFF

        if k == ord('q'):
            break
        elif k == ord('v'):
            validando = not validando
            print(f"[INFO] Validacao {'ON' if validando else 'OFF'}")
        elif k == ord('c'):
            # cadastro só se houver exatamente 1 rosto e descriptor disponível
            if len(last_faces) == 1 and last_descriptor is not None:
                print("\n--- Cadastro ---")
                try:
                    name = input("Nome: ").strip()
                except EOFError:
                    name = ""
                if not name:
                    print("[ERRO] Nome vazio.")
                    continue

                # checar se já existe
                cur = con.execute("SELECT 1 FROM users WHERE name=?;", (name,))
                if cur.fetchone():
                    print("[ERRO] Nome já existe. Escolha outro.")
                    continue

                print("Perfil: [1] Conservador  [2] Moderado  [3] Agressivo")
                profile_map = {"1": "Conservador", "2": "Moderado", "3": "Agressivo"}
                choice = ""
                while choice not in profile_map:
                    try:
                        choice = input("Digite 1/2/3: ").strip()
                    except EOFError:
                        choice = ""
                profile = profile_map[choice]

                insert_user(con, name, profile, last_descriptor.tolist())
                print(f"[OK] {name} ({profile}) cadastrado.")
            else:
                print("[ERRO] Para cadastrar, mantenha APENAS UM rosto visível.")

    cap.release()
    cv2.destroyAllWindows()
    if ser:
        ser.close()

if __name__ == "__main__":
    main()
