#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface gráfica — Sistema de Captura de Leads
Execute: python interface.py   (ou clique duas vezes em PASSO_2_RODAR.bat)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import subprocess
import sys
import os
from pathlib import Path


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Captura de Leads")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self.log_queue = queue.Queue()
        self.buscas = []

        self._build_ui()
        self._poll_log()

    # =========================================================
    #  Construção da interface
    # =========================================================

    def _build_ui(self):

        # ── Cabeçalho ─────────────────────────────────────────
        header = tk.Frame(self, bg="#2c3e50")
        header.pack(fill="x")
        tk.Label(
            header,
            text="🎯  Sistema de Captura de Leads",
            font=("Segoe UI", 13, "bold"),
            bg="#2c3e50", fg="white",
            pady=12, padx=15,
        ).pack(side="left")

        # ── Corpo ──────────────────────────────────────────────
        body = tk.Frame(self, bg="#f5f5f5", padx=15, pady=12)
        body.pack(fill="both", expand=True)

        # ── Seção: Nova busca ──────────────────────────────────
        frame_form = tk.LabelFrame(
            body, text=" Nova busca ",
            bg="#f5f5f5", font=("Segoe UI", 10, "bold"),
            padx=10, pady=8,
        )
        frame_form.pack(fill="x", pady=(0, 10))

        def lbl(text, row, col):
            tk.Label(frame_form, text=text, bg="#f5f5f5",
                     font=("Segoe UI", 10)).grid(
                row=row, column=col, sticky="w", padx=5, pady=4)

        lbl("Tipo de negócio:", 0, 0)
        self.e_negocio = ttk.Entry(frame_form, width=42, font=("Segoe UI", 10))
        self.e_negocio.grid(row=0, column=1, columnspan=3, sticky="w", padx=5, pady=4)
        self.e_negocio.insert(0, "clínicas odontológicas")

        lbl("Cidade:", 1, 0)
        self.e_cidade = ttk.Entry(frame_form, width=24, font=("Segoe UI", 10))
        self.e_cidade.grid(row=1, column=1, sticky="w", padx=5, pady=4)
        self.e_cidade.insert(0, "Curitiba")

        lbl("Estado (UF):", 1, 2)
        self.e_estado = ttk.Entry(frame_form, width=5, font=("Segoe UI", 10))
        self.e_estado.grid(row=1, column=3, sticky="w", padx=5, pady=4)
        self.e_estado.insert(0, "PR")

        lbl("Bairro (opcional):", 2, 0)
        self.e_bairro = ttk.Entry(frame_form, width=42, font=("Segoe UI", 10))
        self.e_bairro.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=4)

        ttk.Button(
            frame_form, text="➕  Adicionar à lista",
            command=self._adicionar,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=5, pady=(6, 2))

        # ── Seção: Lista de buscas ─────────────────────────────
        frame_lista = tk.LabelFrame(
            body, text=" Buscas adicionadas ",
            bg="#f5f5f5", font=("Segoe UI", 10, "bold"),
            padx=10, pady=8,
        )
        frame_lista.pack(fill="x", pady=(0, 10))

        list_inner = tk.Frame(frame_lista, bg="#f5f5f5")
        list_inner.pack(fill="x")

        sb = ttk.Scrollbar(list_inner)
        sb.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_inner, height=4, font=("Segoe UI", 9),
            yscrollcommand=sb.set, selectmode=tk.SINGLE,
            bg="white", relief="solid", bd=1,
        )
        self.listbox.pack(side="left", fill="x", expand=True)
        sb.config(command=self.listbox.yview)

        ttk.Button(
            frame_lista, text="✕  Remover selecionada",
            command=self._remover,
        ).pack(anchor="w", pady=(6, 0))

        # ── Seção: Opções ──────────────────────────────────────
        frame_opt = tk.LabelFrame(
            body, text=" Opções ",
            bg="#f5f5f5", font=("Segoe UI", 10, "bold"),
            padx=10, pady=8,
        )
        frame_opt.pack(fill="x", pady=(0, 12))

        tk.Label(
            frame_opt, text="Quantidade máxima por busca:",
            bg="#f5f5f5", font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w", padx=5, pady=4)

        self.spin = ttk.Spinbox(frame_opt, from_=5, to=200, width=6,
                                font=("Segoe UI", 10))
        self.spin.grid(row=0, column=1, sticky="w", padx=5)
        self.spin.set(40)

        self.var_redes = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame_opt,
            text="Buscar e-mail, Instagram e Facebook nos sites  (recomendado, porém mais lento)",
            variable=self.var_redes,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=4)

        # ── Botão Iniciar ──────────────────────────────────────
        self.btn_iniciar = tk.Button(
            body,
            text="▶   INICIAR CAPTURA",
            font=("Segoe UI", 12, "bold"),
            bg="#27ae60", fg="white",
            activebackground="#1e8449", activeforeground="white",
            relief="flat", padx=30, pady=10,
            cursor="hand2",
            command=self._iniciar,
        )
        self.btn_iniciar.pack(pady=(0, 8))

        # ── Barra de progresso + status ────────────────────────
        self.progress = ttk.Progressbar(body, mode="indeterminate", length=560)
        self.progress.pack(fill="x", padx=5)

        self.lbl_status = tk.Label(
            body, text="Preencha os campos e clique em Iniciar.",
            bg="#f5f5f5", font=("Segoe UI", 9), fg="#777",
        )
        self.lbl_status.pack(pady=(3, 8))

        # ── Log ────────────────────────────────────────────────
        tk.Label(
            body, text="Log de execução:",
            bg="#f5f5f5", font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=5)

        self.log_widget = scrolledtext.ScrolledText(
            body, height=10, font=("Consolas", 9),
            state="disabled", bg="#1e1e1e", fg="#d4d4d4",
            relief="solid", bd=1, wrap="word",
        )
        self.log_widget.pack(fill="x", padx=5, pady=5)

        # ── Botão abrir CSV ────────────────────────────────────
        self.btn_csv = tk.Button(
            body,
            text="📊  Abrir leads.csv no Excel",
            font=("Segoe UI", 10),
            bg="#2980b9", fg="white",
            activebackground="#1a6391", activeforeground="white",
            relief="flat", padx=15, pady=7,
            cursor="hand2", state="disabled",
            command=self._abrir_csv,
        )
        self.btn_csv.pack(pady=(0, 12))

    # =========================================================
    #  Ações dos botões
    # =========================================================

    def _adicionar(self):
        negocio = self.e_negocio.get().strip()
        cidade  = self.e_cidade.get().strip()
        estado  = self.e_estado.get().strip().upper()
        bairro  = self.e_bairro.get().strip()

        if not negocio or not cidade or not estado:
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha ao menos:\n  • Tipo de negócio\n  • Cidade\n  • Estado (UF)",
            )
            return

        if len(estado) != 2:
            messagebox.showwarning("UF inválida",
                                   "Digite as 2 letras do estado. Ex.: SP, RJ, MG, PR")
            return

        termo = (
            f"{negocio} {bairro} {cidade} {estado}"
            if bairro
            else f"{negocio} em {cidade} {estado}"
        )

        if termo in self.buscas:
            messagebox.showinfo("Já existe", "Esta busca já está na lista.")
            return

        self.buscas.append(termo)
        self.listbox.insert(tk.END, f"  •  {termo}")

    def _remover(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.listbox.delete(idx)
            self.buscas.pop(idx)

    def _iniciar(self):
        if not self.buscas:
            messagebox.showwarning(
                "Sem buscas",
                "Adicione pelo menos uma busca antes de iniciar.",
            )
            return

        # Grava configuracao.py com os valores da tela
        cfg_txt = (
            "# Gerado automaticamente pela interface — nao edite manualmente\n"
            f"BUSCAS = {self.buscas!r}\n"
            f"MAX_POR_BUSCA = {int(self.spin.get())}\n"
            f"EXTRAIR_DADOS_SITE = {self.var_redes.get()}\n"
            "SAIDA_CSV = 'leads.csv'\n"
        )
        Path("configuracao.py").write_text(cfg_txt, encoding="utf-8")

        self.btn_iniciar.config(state="disabled")
        self.btn_csv.config(state="disabled")
        self.progress.start(10)
        self.lbl_status.config(text="Capturando leads... não feche esta janela.", fg="#555")
        self._log_clear()
        self._log("=" * 52 + "\n INICIANDO CAPTURA\n" + "=" * 52 + "\n\n")

        threading.Thread(target=self._executar, daemon=True).start()

    def _executar(self):
        """Roda captura_leads.py como subprocesso e redireciona o output pro log."""
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            proc = subprocess.Popen(
                [sys.executable, "-u", "captura_leads.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            for linha in proc.stdout:
                self.log_queue.put(linha)

            proc.wait()

            self.log_queue.put(
                "__DONE__" if proc.returncode == 0 else "__ERROR__"
            )

        except Exception as exc:
            self.log_queue.put(f"\n[ERRO INTERNO] {exc}\n")
            self.log_queue.put("__ERROR__")

    # =========================================================
    #  Atualização da UI (thread-safe via queue)
    # =========================================================

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__DONE__":
                    self._on_done()
                elif msg == "__ERROR__":
                    self._on_error()
                else:
                    self._log(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _log(self, text):
        self.log_widget.config(state="normal")
        self.log_widget.insert(tk.END, text)
        self.log_widget.see(tk.END)
        self.log_widget.config(state="disabled")

    def _log_clear(self):
        self.log_widget.config(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.config(state="disabled")

    def _on_done(self):
        self.progress.stop()
        self.lbl_status.config(
            text="✅  Concluído! O arquivo leads.csv está pronto.", fg="#27ae60"
        )
        self.btn_iniciar.config(state="normal")
        self.btn_csv.config(state="normal")
        messagebox.showinfo(
            "Concluído!",
            "Captura finalizada com sucesso!\n\n"
            "Clique em  📊 Abrir leads.csv  para ver os resultados.",
        )

    def _on_error(self):
        self.progress.stop()
        self.lbl_status.config(
            text="❌  Ocorreu um erro. Veja o log acima.", fg="#e74c3c"
        )
        self.btn_iniciar.config(state="normal")
        messagebox.showerror(
            "Erro durante a captura",
            "Algo deu errado.\nVeja o log na tela para mais detalhes.\n\n"
            "Se o problema persistir, mande uma foto do log para suporte.",
        )

    def _abrir_csv(self):
        csv_path = Path("leads.csv").resolve()
        if csv_path.exists():
            os.startfile(str(csv_path))
        else:
            messagebox.showerror(
                "Arquivo não encontrado",
                "O arquivo leads.csv ainda não existe.\nRode a captura primeiro.",
            )


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
