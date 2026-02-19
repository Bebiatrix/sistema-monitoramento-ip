from flask import Flask, request, render_template_string
import sqlite3
import re

app = Flask(__name__)

# Criar banco automaticamente
def init_db():
    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS acessos (
        id INTEGER,
        nome TEXT,
        ip TEXT,
        data TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bans (
        id INTEGER,
        motivo TEXT,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Sistema de IP</title>
</head>
<body style="font-family: Arial; background:#111; color:white; padding:20px;">

<h2>📊 Sistema de Monitoramento de IP</h2>

<form method="post">
<h3>📥 Colar Logs de Acesso:</h3>
<textarea name="logs_acesso" rows="10" cols="100"></textarea>

<h3>🚫 Colar Logs de Ban:</h3>
<textarea name="logs_ban" rows="5" cols="100"></textarea>

<br><br>
<button type="submit">Processar</button>
</form>

<hr>

<h3>🏆 Ranking de IPs</h3>
{{ranking}}

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    ranking_html = ""

    if request.method == "POST":
        logs_acesso = request.form.get("logs_acesso", "")
        logs_ban = request.form.get("logs_ban", "")

        conn = sqlite3.connect("banco.db")
        cursor = conn.cursor()

        # Processar logs de acesso
        blocos = logs_acesso.split("Alta RJ Logs")
        for bloco in blocos:
            id_match = re.search(r"\[ID\]\s*(\d+)", bloco)
            nome_match = re.search(r"\[NOME\]\s*(.+)", bloco)
            ip_match = re.search(r"\[IP\]\s*([\d\.]+)", bloco)
            data_match = re.search(r"\[DATA\]\s*(.+)", bloco)

            if id_match and nome_match and ip_match and data_match:
                cursor.execute("INSERT INTO acessos VALUES (?, ?, ?, ?)",
                               (int(id_match.group(1)),
                                nome_match.group(1),
                                ip_match.group(1),
                                data_match.group(1)))

        # Processar logs de ban
        ban_match = re.findall(r"baniu o usuário (\d+) pelo motivo (.+)\.", logs_ban)
        for ban in ban_match:
            cursor.execute("INSERT INTO bans VALUES (?, ?, datetime('now'))",
                           (int(ban[0]), ban[1]))

        conn.commit()

        # Gerar ranking
        cursor.execute("""
        SELECT ip, COUNT(*) as total
        FROM acessos
        GROUP BY ip
        ORDER BY total DESC
        """)

        ips = cursor.fetchall()

        for ip, total in ips:
            cursor.execute("""
            SELECT COUNT(*)
            FROM bans
            WHERE id IN (SELECT id FROM acessos WHERE ip=?)
            """, (ip,))
            bans_count = cursor.fetchone()[0]

            if bans_count > 0:
                status = "🔴 IP CRÍTICO (Ban por Hacker)"
            elif total > 1:
                status = "🟠 IP SUSPEITO"
            else:
                status = "🟢 IP Normal"

            ranking_html += f"<p><b>{ip}</b> — {total} acessos — {status}</p>"

        conn.close()

    return render_template_string(HTML, ranking=ranking_html)

if __name__ == "__main__":
    app.run()
