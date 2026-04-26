import sys
import time
import ctypes
import threading
import msvcrt
import winsound
import numpy as np
import cv2
import mss

IMAGENS_REFERENCIA = [
    r"C:\GitHub\identificação-de-tela\referencia.png",
    r"C:\GitHub\identificação-de-tela\referencia2.png",
    r"C:\GitHub\identificação-de-tela\referencia3.png",
]

CONFIANCA_MINIMA = 0.60
INTERVALO_VERIFICACAO = 0.5
REGIAO_MONITOR = None
ESCALA_MINIMA = 0.30
ESCALA_MAXIMA = 1.00
ESCALA_PASSO  = 0.05
BEEP_FREQUENCIA = 1000
BEEP_DURACAO    = 400


def carregar_referencia(caminho: str) -> np.ndarray:
    buf = np.fromfile(caminho, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"[ERRO] Não foi possível carregar '{caminho}'.")
        print("       Verifique se o arquivo existe e é uma imagem válida.")
        sys.exit(1)
    print(f"[OK] Imagem de referência carregada: {caminho} ({img.shape[1]}x{img.shape[0]} px)")
    return img


def capturar_tela(sct: mss.mss, regiao: dict | None) -> np.ndarray:
    monitor = regiao if regiao else sct.monitors[0]
    screenshot = sct.grab(monitor)
    frame = np.frombuffer(screenshot.raw, dtype=np.uint8)
    frame = frame.reshape((screenshot.height, screenshot.width, 4))
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)


def detectar_imagem(tela: np.ndarray, referencia: np.ndarray, confianca: float) -> tuple[bool, float, tuple, float]:
    h_ref, w_ref = referencia.shape[:2]
    h_tela, w_tela = tela.shape[:2]

    melhor_val   = 0.0
    melhor_loc   = (0, 0)
    melhor_escala = 1.0

    escala = ESCALA_MINIMA
    while escala <= ESCALA_MAXIMA + 1e-9:
        novo_w = int(w_ref * escala)
        novo_h = int(h_ref * escala)

        if novo_w >= 1 and novo_h >= 1 and novo_w <= w_tela and novo_h <= h_tela:
            ref_redim = cv2.resize(referencia, (novo_w, novo_h), interpolation=cv2.INTER_AREA)
            resultado = cv2.matchTemplate(tela, ref_redim, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(resultado)
            if max_val > melhor_val:
                melhor_val    = max_val
                melhor_loc    = max_loc
                melhor_escala = escala

        escala = round(escala + ESCALA_PASSO, 10)

    centro = (
        melhor_loc[0] + int(w_ref * melhor_escala) // 2,
        melhor_loc[1] + int(h_ref * melhor_escala) // 2,
    )
    return melhor_val >= confianca, float(melhor_val), centro, melhor_escala


_parar_beep = threading.Event()
_thread_beep: threading.Thread | None = None


def _definir_volume_maximo() -> None:
    try:
        ctypes.WinDLL("winmm").waveOutSetVolume(0, 0xFFFFFFFF)
        print("[OK] Volume do sistema definido para o máximo.")
    except Exception as e:
        print(f"[AVISO] Não foi possível ajustar o volume: {e}")


def _loop_beep() -> None:
    while not _parar_beep.is_set():
        winsound.Beep(BEEP_FREQUENCIA, BEEP_DURACAO)


def iniciar_som() -> None:
    global _thread_beep
    _parar_beep.clear()
    if _thread_beep is None or not _thread_beep.is_alive():
        _thread_beep = threading.Thread(target=_loop_beep, daemon=True)
        _thread_beep.start()


def parar_som() -> None:
    global _thread_beep
    _parar_beep.set()
    if _thread_beep:
        _thread_beep.join(timeout=2.0)
        _thread_beep = None


def main() -> None:
    _definir_volume_maximo()
    referencias = [carregar_referencia(c) for c in IMAGENS_REFERENCIA]

    regiao_str = (
        f"top={REGIAO_MONITOR['top']} left={REGIAO_MONITOR['left']} "
        f"{REGIAO_MONITOR['width']}x{REGIAO_MONITOR['height']}"
        if REGIAO_MONITOR else "tela inteira"
    )
    print(f"[INFO] Monitorando: {regiao_str}")
    print(f"[INFO] Confiança mínima: {CONFIANCA_MINIMA:.0%} | Intervalo: {INTERVALO_VERIFICACAO}s")
    print("[INFO] Pressione qualquer tecla para parar o alerta | Ctrl+C para encerrar.\n")

    alertas_ativos = [False] * len(referencias)
    som_tocando = False

    with mss.mss() as sct:
        while True:
            try:
                inicio = time.perf_counter()

                if msvcrt.kbhit():
                    msvcrt.getch()
                    if som_tocando:
                        parar_som()
                        som_tocando = False
                        alertas_ativos = [False] * len(referencias)
                        print(f"[{time.strftime('%H:%M:%S')}] Alerta encerrado pelo usuário.")

                tela = capturar_tela(sct, REGIAO_MONITOR)

                for i, ref in enumerate(referencias):
                    enc, conf, pos, esc = detectar_imagem(tela, ref, CONFIANCA_MINIMA)
                    if enc:
                        if not alertas_ativos[i]:
                            timestamp = time.strftime("%H:%M:%S")
                            print(
                                f"[{timestamp}] IMAGEM DETECTADA! (referencia{i + 1}) "
                                f"Confiança: {conf:.1%} | "
                                f"Escala: {esc:.0%} | "
                                f"Posição: x={pos[0]}, y={pos[1]}"
                            )
                            alertas_ativos[i] = True
                            if not som_tocando:
                                iniciar_som()
                                som_tocando = True
                    else:
                        if alertas_ativos[i]:
                            alertas_ativos[i] = False
                            print(f"[{time.strftime('%H:%M:%S')}] referencia{i + 1} saiu da tela.")

                tempo_decorrido = time.perf_counter() - inicio
                espera = max(0.0, INTERVALO_VERIFICACAO - tempo_decorrido)
                time.sleep(espera)

            except KeyboardInterrupt:
                print("\n[INFO] Monitoramento encerrado pelo usuário.")
                parar_som()
                break
            except Exception as e:
                print(f"[AVISO] Erro durante verificação: {e}")
                time.sleep(INTERVALO_VERIFICACAO)


if __name__ == "__main__":
    main()
