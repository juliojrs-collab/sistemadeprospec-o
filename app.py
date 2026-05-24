#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor Flask — Sistema de Captura de Leads
"""

import io
import csv
import uuid
import threading
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, Response
from scraper import executar_busca, COLUNAS

app = Flask(__name__)

# ──────────────────────────────────────────────────────────────
#  Armazenamento de jobs em memória
#  job = { status, data, log, erro, criado_em }
# ──────────────────────────────────────────────────────────────
_jobs: dict = {}
_lock = threading.Lock()


def _limpar_jobs_antigos():
    """Remove jobs com mais de 2 horas para não vazar memória."""
    limite = datetime.now() - timedelta(hours=2)
    with _lock:
        velhos = [jid for jid, j in _jobs.items() if j["criado_em"] < limite]
        for jid in velhos:
            del _jobs[jid]


def _log(job_id: str, msg: str):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["log"].append(msg)


# ──────────────────────────────────────────────────────────────
#  Rotas
# ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/buscar", methods=["POST"])
def buscar():
    body = request.get_json(force=True)

    tipo      = (body.get("tipo_negocio") or "").strip()
    cidade    = (body.get("cidade") or "").strip()
    estado    = (body.get("estado") or "").strip()
    bairro    = (body.get("bairro") or "").strip()
    quantidade = int(body.get("quantidade", 40))
    extrair   = bool(body.get("extrair_dados", True))

    if not tipo or not cidade or not estado:
        return jsonify({"erro": "Preencha o tipo de negócio, a cidade e o estado."}), 400

    termo = (
        f"{tipo} {bairro} {cidade} {estado}"
        if bairro
        else f"{tipo} em {cidade} {estado}"
    )

    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status":    "running",
            "data":      [],
            "log":       [],
            "erro":      "",
            "criado_em": datetime.now(),
        }

    _limpar_jobs_antigos()

    threading.Thread(
        target=_executar,
        args=(job_id, termo, quantidade, extrair),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id})


def _executar(job_id, termo, quantidade, extrair):
    try:
        leads = executar_busca(
            termo=termo,
            quantidade=quantidade,
            extrair_dados=extrair,
            log_fn=lambda msg: _log(job_id, msg),
        )
        with _lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["data"]   = leads
    except Exception as exc:
        with _lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["erro"]   = str(exc)


@app.route("/status/<job_id>")
def status(job_id):
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"erro": "Job não encontrado"}), 404

    return jsonify({
        "status": job["status"],
        "total":  len(job["data"]),
        "log":    "".join(job["log"][-80:]),   # últimas 80 mensagens
        "erro":   job["erro"],
    })


@app.route("/resultado/<job_id>")
def resultado(job_id):
    with _lock:
        job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"erro": "Resultado não disponível"}), 404
    return jsonify({"data": job["data"]})


@app.route("/download/<job_id>")
def download(job_id):
    with _lock:
        job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return "Não disponível", 404

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUNAS)
    writer.writeheader()
    for row in job["data"]:
        writer.writerow({c: row.get(c, "") for c in COLUNAS})

    # UTF-8 com BOM — abre certinho no Excel
    content = "﻿" + out.getvalue()

    return Response(
        content.encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
