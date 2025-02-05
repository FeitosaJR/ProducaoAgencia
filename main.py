import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import re
import shutil
import pandas as pd

# Constantes
ARQUIVO_DB = "producao.db"
LISTA_PAS = ["PA01", "PA02", "PA03", "PA04", "PA05", "PA06", "PA07", "PA08", "PA09", "PA10", "PA97"]

# Variável global para armazenar o índice do registro em edição
registro_em_edicao = None

# Funções de Validação
def validar_cpf_cnpj(cpf_cnpj):
    """
    Valida CPF ou CNPJ.
    Retorna True se for válido, False caso contrário.
    """
    cpf_cnpj = re.sub(r'[^0-9]', '', cpf_cnpj)
    if len(cpf_cnpj) == 11:  # CPF
        if cpf_cnpj == cpf_cnpj[0] * 11:
            return False
        return True
    elif len(cpf_cnpj) == 14:  # CNPJ
        if cpf_cnpj == cpf_cnpj[0] * 14:
            return False
        return True
    return False

def validar_data(data):
    """
    Valida a data no formato DD-MM-AAAA.
    Retorna True se for válida, False caso contrário.
    """
    try:
        datetime.strptime(data, "%d-%m-%Y")
        return True
    except ValueError:
        return False

def validar_valor(valor):
    """
    Valida o valor monetário.
    Retorna True se for válido, False caso contrário.
    """
    try:
        valor_limpo = valor.replace("R$", "").replace(",", ".").strip()
        float(valor_limpo)
        return True
    except ValueError:
        return False

# Funções de Banco de Dados
def conectar_db():
    """
    Conecta ao banco de dados SQLite.
    Retorna a conexão.
    """
    return sqlite3.connect(ARQUIVO_DB)

def criar_tabela_pas():
    """
    Cria a tabela de PAs e a popula com dados iniciais, se necessário.
    """
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )
        ''')
        cursor.execute("SELECT COUNT(*) FROM pas")
        if cursor.fetchone()[0] == 0:  # Se a tabela estiver vazia
            cursor.executemany('''
                INSERT INTO pas (nome) VALUES (?)
            ''', [(pa,) for pa in LISTA_PAS])
        conn.commit()

def carregar_pas():
    """
    Carrega a lista de PAs do banco de dados.
    Retorna uma lista de PAs.
    """
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pas'")
        if cursor.fetchone() is None:
            criar_tabela_pas()  # Cria a tabela se não existir
        cursor.execute("SELECT nome FROM pas")
        return [row[0] for row in cursor.fetchall()]

def criar_tabela_producao():
    """
    Cria a tabela de produção, se não existir.
    """
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS producao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pa TEXT NOT NULL,
                colaborador TEXT NOT NULL,
                data TEXT NOT NULL,
                cpf_cnpj TEXT NOT NULL,
                cliente TEXT NOT NULL,
                produto TEXT NOT NULL,
                status TEXT NOT NULL,
                valor TEXT NOT NULL,
                observacoes TEXT
            )
        ''')
        conn.commit()

# Funções de Interface Gráfica
def registrar_producao():
    """
    Registra ou atualiza uma produção no banco de dados.
    """
    global registro_em_edicao

    pa = combo_pa.get().upper()
    nome_colaborador = entry_colaborador.get().upper()
    data = entry_data.get()
    cpf_cnpj = entry_cpf_cnpj.get().upper()
    nome_cliente = entry_cliente.get().upper()
    produto = entry_produto.get().upper()
    status = combo_status.get().upper()
    valor_captado = entry_valor.get().upper()
    observacoes = entry_observacoes.get().upper()

    if not pa or not nome_colaborador or not cpf_cnpj or not nome_cliente or not produto or not status or not valor_captado:
        messagebox.showwarning("Atenção", "Todos os campos devem ser preenchidos!")
        return

    if not validar_cpf_cnpj(cpf_cnpj):
        messagebox.showwarning("Atenção", "CPF/CNPJ inválido!")
        return

    if not validar_data(data):
        messagebox.showwarning("Atenção", "Data inválida! Use o formato DD-MM-AAAA.")
        return

    if not validar_valor(valor_captado):
        messagebox.showwarning("Atenção", "Valor inválido! Insira um valor monetário válido.")
        return

    try:
        with conectar_db() as conn:
            cursor = conn.cursor()
            if registro_em_edicao is None:
                cursor.execute('''
                    INSERT INTO producao (pa, colaborador, data, cpf_cnpj, cliente, produto, status, valor, observacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pa, nome_colaborador, data, cpf_cnpj, nome_cliente, produto, status, valor_captado, observacoes))
            else:
                cursor.execute('''
                    UPDATE producao
                    SET pa=?, colaborador=?, data=?, cpf_cnpj=?, cliente=?, produto=?, status=?, valor=?, observacoes=?
                    WHERE id=?
                ''', (pa, nome_colaborador, data, cpf_cnpj, nome_cliente, produto, status, valor_captado, observacoes, registro_em_edicao))
            conn.commit()

        messagebox.showinfo("Sucesso", "Produção registrada com sucesso!")
        limpar_campos()
        if registro_em_edicao is not None:
            registro_em_edicao = None  # Reseta o registro em edição
            abrir_tela_registros()  # Atualiza a lista de registros
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao registrar a produção: {e}")

def limpar_campos():
    """
    Limpa todos os campos do formulário.
    """
    global registro_em_edicao
    combo_pa.set("")
    entry_colaborador.delete(0, tk.END)
    entry_data.delete(0, tk.END)
    entry_cpf_cnpj.delete(0, tk.END)
    entry_cliente.delete(0, tk.END)
    entry_produto.delete(0, tk.END)
    combo_status.set("")
    entry_valor.delete(0, tk.END)
    entry_observacoes.delete(0, tk.END)
    registro_em_edicao = None
    btn_salvar_edicao.pack_forget()  # Oculta o botão "Salvar Edição"

def ordenar_coluna(tree, col, reverse):
    """
    Ordena as colunas da Treeview.
    """
    dados = [(tree.set(item, col), item) for item in tree.get_children("")]
    dados.sort(reverse=reverse)
    for index, (valor, item) in enumerate(dados):
        tree.move(item, "", index)
    tree.heading(col, command=lambda: ordenar_coluna(tree, col, not reverse))

def abrir_tela_registros():
    """
    Abre a tela de registros com filtros e Treeview.
    """
    global tree, janela_registros, entry_filtro_colaborador, entry_filtro_cliente, entry_filtro_produto, entry_filtro_data, entry_filtro_pa, entry_filtro_data_inicio, entry_filtro_data_fim

    janela_registros = tk.Toplevel()
    janela_registros.title("Registros de Produção")
    janela_registros.geometry("1000x500")

    # Frame de filtros
    frame_filtros = tk.Frame(janela_registros)
    frame_filtros.pack(pady=10, fill="x")

    tk.Label(frame_filtros, text="PA:").grid(row=0, column=0, padx=5)
    entry_filtro_pa = ttk.Combobox(frame_filtros, values=carregar_pas())
    entry_filtro_pa.grid(row=0, column=1, padx=5)

    tk.Label(frame_filtros, text="Colaborador:").grid(row=0, column=2, padx=5)
    entry_filtro_colaborador = tk.Entry(frame_filtros)
    entry_filtro_colaborador.grid(row=0, column=3, padx=5)

    tk.Label(frame_filtros, text="Cliente:").grid(row=0, column=4, padx=5)
    entry_filtro_cliente = tk.Entry(frame_filtros)
    entry_filtro_cliente.grid(row=0, column=5, padx=5)

    tk.Label(frame_filtros, text="Produto:").grid(row=1, column=0, padx=5)
    entry_filtro_produto = tk.Entry(frame_filtros)
    entry_filtro_produto.grid(row=1, column=1, padx=5)

    tk.Label(frame_filtros, text="Data (AAAA, MM-AAAA ou DD-MM-AAAA):").grid(row=1, column=2, padx=5)
    entry_filtro_data = tk.Entry(frame_filtros)
    entry_filtro_data.grid(row=1, column=3, padx=5)

    tk.Label(frame_filtros, text="Data Início (DD-MM-AAAA):").grid(row=2, column=0, padx=5)
    entry_filtro_data_inicio = tk.Entry(frame_filtros)
    entry_filtro_data_inicio.grid(row=2, column=1, padx=5)

    tk.Label(frame_filtros, text="Data Fim (DD-MM-AAAA):").grid(row=2, column=2, padx=5)
    entry_filtro_data_fim = tk.Entry(frame_filtros)
    entry_filtro_data_fim.grid(row=2, column=3, padx=5)

    btn_filtrar = tk.Button(frame_filtros, text="Filtrar", command=filtrar_registros)
    btn_filtrar.grid(row=2, column=4, padx=5)

    btn_limpar_filtros = tk.Button(frame_filtros, text="Limpar Filtros", command=limpar_filtros)
    btn_limpar_filtros.grid(row=2, column=5, padx=5)

    btn_gerar_relatorio = tk.Button(frame_filtros, text="Gerar Relatório", command=gerar_relatorio_filtrado)
    btn_gerar_relatorio.grid(row=2, column=6, padx=5)

    btn_exportar_excel = tk.Button(frame_filtros, text="Exportar para Excel", command=exportar_para_excel)
    btn_exportar_excel.grid(row=2, column=7, padx=5)

    # Frame para a Treeview e barras de rolagem
    frame_treeview = tk.Frame(janela_registros)
    frame_treeview.pack(expand=True, fill="both", padx=10, pady=10)

    # Treeview
    tree = ttk.Treeview(frame_treeview, columns=("PA", "Colaborador", "Data", "CPF/CNPJ", "Cliente", "Produto", "Status", "Valor", "Observações"), show="headings")
    tree.heading("PA", text="PA", command=lambda: ordenar_coluna(tree, "PA", False))
    tree.heading("Colaborador", text="Colaborador", command=lambda: ordenar_coluna(tree, "Colaborador", False))
    tree.heading("Data", text="Data", command=lambda: ordenar_coluna(tree, "Data", False))
    tree.heading("CPF/CNPJ", text="CPF/CNPJ", command=lambda: ordenar_coluna(tree, "CPF/CNPJ", False))
    tree.heading("Cliente", text="Cliente", command=lambda: ordenar_coluna(tree, "Cliente", False))
    tree.heading("Produto", text="Produto", command=lambda: ordenar_coluna(tree, "Produto", False))
    tree.heading("Status", text="Status", command=lambda: ordenar_coluna(tree, "Status", False))
    tree.heading("Valor", text="Valor", command=lambda: ordenar_coluna(tree, "Valor", False))
    tree.heading("Observações", text="Observações", command=lambda: ordenar_coluna(tree, "Observações", False))

    # Barra de rolagem vertical
    scrollbar_vertical = ttk.Scrollbar(frame_treeview, orient="vertical", command=tree.yview)
    scrollbar_vertical.pack(side="right", fill="y")

    # Barra de rolagem horizontal
    scrollbar_horizontal = ttk.Scrollbar(frame_treeview, orient="horizontal", command=tree.xview)
    scrollbar_horizontal.pack(side="bottom", fill="x")

    # Configura a Treeview para usar as barras de rolagem
    tree.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
    tree.pack(expand=True, fill="both")

    tree.bind("<Double-1>", carregar_para_edicao)
    exibir_registros()

    # Botão de exclusão
    btn_excluir = tk.Button(janela_registros, text="Excluir", command=excluir_registro)
    btn_excluir.pack(pady=5)

def exibir_registros():
    """
    Exibe todos os registros na Treeview.
    """
    tree.delete(*tree.get_children())
    with conectar_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM producao")
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row[1:])

def filtrar_registros():
    """
    Filtra os registros com base nos critérios fornecidos.
    """
    pa = entry_filtro_pa.get().upper()
    colaborador = entry_filtro_colaborador.get().upper()
    cliente = entry_filtro_cliente.get().upper()
    produto = entry_filtro_produto.get().upper()
    data_filtro = entry_filtro_data.get()
    data_inicio = entry_filtro_data_inicio.get()
    data_fim = entry_filtro_data_fim.get()

    tree.delete(*tree.get_children())
    with conectar_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM producao WHERE 1=1"
        params = []

        if pa:
            query += " AND pa = ?"
            params.append(pa)
        if colaborador:
            query += " AND colaborador LIKE ?"
            params.append(f"%{colaborador}%")
        if cliente:
            query += " AND cliente LIKE ?"
            params.append(f"%{cliente}%")
        if produto:
            query += " AND produto LIKE ?"
            params.append(f"%{produto}%")
        if data_filtro.strip():
            if len(data_filtro) == 4:  # Filtro por ano (AAAA)
                query += " AND strftime('%Y', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 7:  # Filtro por ano e mês (AAAA-MM)
                query += " AND strftime('%Y-%m', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 10:  # Filtro por data completa (AAAA-MM-DD)
                query += " AND data = ?"
                params.append(data_filtro)
        if data_inicio.strip() and data_fim.strip():
            try:
                # Converte as datas para o formato YYYY-MM-DD
                data_inicio_formatada = datetime.strptime(data_inicio, "%d-%m-%Y").strftime("%Y-%m-%d")
                data_fim_formatada = datetime.strptime(data_fim, "%d-%m-%Y").strftime("%Y-%m-%d")
                query += " AND data BETWEEN ? AND ?"
                params.extend([data_inicio_formatada, data_fim_formatada])
            except ValueError:
                messagebox.showwarning("Atenção", "Formato de data inválido! Use DD-MM-AAAA.")
                return

        cursor.execute(query, params)
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row[1:])

def limpar_filtros():
    """
    Limpa os filtros e exibe todos os registros.
    """
    entry_filtro_pa.set("")
    entry_filtro_colaborador.delete(0, tk.END)
    entry_filtro_cliente.delete(0, tk.END)
    entry_filtro_produto.delete(0, tk.END)
    entry_filtro_data.delete(0, tk.END)
    entry_filtro_data_inicio.delete(0, tk.END)
    entry_filtro_data_fim.delete(0, tk.END)
    exibir_registros()

def gerar_relatorio_filtrado():
    """
    Gera um relatório de valor captado por colaborador com base nos filtros.
    """
    pa = entry_filtro_pa.get().upper()
    colaborador = entry_filtro_colaborador.get().upper()
    cliente = entry_filtro_cliente.get().upper()
    produto = entry_filtro_produto.get().upper()
    data_filtro = entry_filtro_data.get()
    data_inicio = entry_filtro_data_inicio.get()
    data_fim = entry_filtro_data_fim.get()

    relatorio = {}
    with conectar_db() as conn:
        cursor = conn.cursor()
        query = "SELECT colaborador, valor FROM producao WHERE 1=1"
        params = []

        if pa:
            query += " AND pa = ?"
            params.append(pa)
        if colaborador:
            query += " AND colaborador LIKE ?"
            params.append(f"%{colaborador}%")
        if cliente:
            query += " AND cliente LIKE ?"
            params.append(f"%{cliente}%")
        if produto:
            query += " AND produto LIKE ?"
            params.append(f"%{produto}%")
        if data_filtro.strip():
            if len(data_filtro) == 4:  # Filtro por ano (AAAA)
                query += " AND strftime('%Y', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 7:  # Filtro por ano e mês (AAAA-MM)
                query += " AND strftime('%Y-%m', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 10:  # Filtro por data completa (AAAA-MM-DD)
                query += " AND data = ?"
                params.append(data_filtro)
        if data_inicio.strip() and data_fim.strip():
            try:
                # Converte as datas para o formato YYYY-MM-DD
                data_inicio_formatada = datetime.strptime(data_inicio, "%d-%m-%Y").strftime("%Y-%m-%d")
                data_fim_formatada = datetime.strptime(data_fim, "%d-%m-%Y").strftime("%Y-%m-%d")
                query += " AND data BETWEEN ? AND ?"
                params.extend([data_inicio_formatada, data_fim_formatada])
            except ValueError:
                messagebox.showwarning("Atenção", "Formato de data inválido! Use DD-MM-AAAA.")
                return

        cursor.execute(query, params)
        for row in cursor.fetchall():
            colaborador_nome = row[0]
            valor = float(row[1].replace("R$", "").replace(",", "").strip())
            if colaborador_nome in relatorio:
                relatorio[colaborador_nome] += valor
            else:
                relatorio[colaborador_nome] = valor

    # Exibir relatório em uma nova janela
    janela_relatorio = tk.Toplevel()
    janela_relatorio.title("Relatório de Produção")
    tk.Label(janela_relatorio, text="Relatório de Valor Captado por Colaborador", font=("Arial", 12)).pack(pady=10)
    for colaborador, valor in relatorio.items():
        tk.Label(janela_relatorio, text=f"{colaborador}: R$ {valor:.2f}").pack()

def carregar_para_edicao(event):
    """
    Carrega um registro selecionado na Treeview para edição.
    """
    global registro_em_edicao

    selecionado = tree.focus()
    if not selecionado:
        return

    valores = tree.item(selecionado, "values")
    if valores:
        # Obtém o ID do registro selecionado
        with conectar_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM producao WHERE pa=? AND colaborador=? AND data=? AND cpf_cnpj=? AND cliente=? AND produto=? AND status=? AND valor=? AND observacoes=?", valores)
            registro_em_edicao = cursor.fetchone()[0]

        # Preenche os campos do formulário com os valores do registro selecionado
        combo_pa.set(valores[0])
        entry_colaborador.delete(0, tk.END)
        entry_colaborador.insert(0, valores[1])
        entry_data.delete(0, tk.END)
        entry_data.insert(0, datetime.strptime(valores[2], "%d-%m-%Y").strftime("%d-%m-%Y"))
        entry_cpf_cnpj.delete(0, tk.END)
        entry_cpf_cnpj.insert(0, valores[3])
        entry_cliente.delete(0, tk.END)
        entry_cliente.insert(0, valores[4])
        entry_produto.delete(0, tk.END)
        entry_produto.insert(0, valores[5])
        combo_status.set(valores[6])
        entry_valor.delete(0, tk.END)
        entry_valor.insert(0, valores[7])
        entry_observacoes.delete(0, tk.END)
        entry_observacoes.insert(0, valores[8])

        # Exibe o botão "Salvar Edição"
        btn_salvar_edicao.pack(pady=5)
        # Fecha a janela de registros
        janela_registros.destroy()

def excluir_registro():
    """
    Exclui um registro selecionado na Treeview.
    """
    selecionado = tree.focus()
    if not selecionado:
        return
    confirmacao = messagebox.askyesno("Confirmação", "Tem certeza que deseja excluir este registro?")
    if confirmacao:
        valores = tree.item(selecionado, "values")
        with conectar_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM producao WHERE pa=? AND colaborador=? AND data=? AND cpf_cnpj=? AND cliente=? AND produto=? AND status=? AND valor=? AND observacoes=?", valores)
            conn.commit()
        exibir_registros()

def exportar_para_excel():
    """
    Exporta os registros filtrados para um arquivo Excel.
    """
    try:
        pa = entry_filtro_pa.get().upper()
        colaborador = entry_filtro_colaborador.get().upper()
        cliente = entry_filtro_cliente.get().upper()
        produto = entry_filtro_produto.get().upper()
        data_filtro = entry_filtro_data.get()
        data_inicio = entry_filtro_data_inicio.get()
        data_fim = entry_filtro_data_fim.get()

        query = "SELECT * FROM producao WHERE 1=1"
        params = []

        if pa:
            query += " AND pa = ?"
            params.append(pa)
        if colaborador:
            query += " AND colaborador LIKE ?"
            params.append(f"%{colaborador}%")
        if cliente:
            query += " AND cliente LIKE ?"
            params.append(f"%{cliente}%")
        if produto:
            query += " AND produto LIKE ?"
            params.append(f"%{produto}%")
        if data_filtro.strip():
            if len(data_filtro) == 4:  # Filtro por ano (AAAA)
                query += " AND strftime('%Y', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 7:  # Filtro por ano e mês (AAAA-MM)
                query += " AND strftime('%Y-%m', data) = ?"
                params.append(data_filtro)
            elif len(data_filtro) == 10:  # Filtro por data completa (AAAA-MM-DD)
                query += " AND data = ?"
                params.append(data_filtro)
        if data_inicio.strip() and data_fim.strip():
            try:
                # Converte as datas para o formato YYYY-MM-DD
                data_inicio_formatada = datetime.strptime(data_inicio, "%d-%m-%Y").strftime("%Y-%m-%d")
                data_fim_formatada = datetime.strptime(data_fim, "%d-%m-%Y").strftime("%Y-%m-%d")
                query += " AND data BETWEEN ? AND ?"
                params.extend([data_inicio_formatada, data_fim_formatada])
            except ValueError:
                messagebox.showwarning("Atenção", "Formato de data inválido! Use DD-MM-AAAA.")
                return

        with conectar_db() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            df.columns = [coluna.upper() for coluna in df.columns]
            caminho_arquivo = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                title="Salvar como"
            )
            if caminho_arquivo:
                df.to_excel(caminho_arquivo, index=False)
                messagebox.showinfo("Sucesso", f"Dados exportados com sucesso para:\n{caminho_arquivo}")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao exportar os dados: {e}")

def fazer_backup():
    """
    Cria um backup do banco de dados.
    """
    try:
        data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(ARQUIVO_DB, f"backup_{data_hora}.db")
        messagebox.showinfo("Backup", f"Backup realizado com sucesso: backup_{data_hora}.db")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao criar backup: {e}")

# Criando a janela principal
janela = tk.Tk()
janela.title("Controle de Produção")
janela.geometry("350x500")

# Criando os widgets
tk.Label(janela, text="PA:").pack()
combo_pa = ttk.Combobox(janela, values=carregar_pas())
combo_pa.pack()

tk.Label(janela, text="Nome do Colaborador:").pack()
entry_colaborador = tk.Entry(janela)
entry_colaborador.pack()

tk.Label(janela, text="CPF/CNPJ do Cliente:").pack()
entry_cpf_cnpj = tk.Entry(janela)
entry_cpf_cnpj.pack()

tk.Label(janela, text="Nome do Cliente:").pack()
entry_cliente = tk.Entry(janela)
entry_cliente.pack()

tk.Label(janela, text="Produto Adquirido:").pack()
entry_produto = tk.Entry(janela)
entry_produto.pack()

tk.Label(janela, text="Data (DD-MM-AAAA):").pack()
entry_data = tk.Entry(janela)
entry_data.pack()

tk.Label(janela, text="Status:").pack()
combo_status = ttk.Combobox(janela, values=["EM ANDAMENTO", "CONCLUÍDO", "CANCELADO"])
combo_status.pack()

tk.Label(janela, text="Valor Captado (R$):").pack()
entry_valor = tk.Entry(janela)
entry_valor.pack()

tk.Label(janela, text="Observações:").pack()
entry_observacoes = tk.Entry(janela)
entry_observacoes.pack()

# Botões
btn_registrar = tk.Button(janela, text="Registrar Produção", command=registrar_producao)
btn_registrar.pack(pady=5)

btn_ver_registros = tk.Button(janela, text="Exibir Registros", command=abrir_tela_registros)
btn_ver_registros.pack(pady=5)

btn_salvar_edicao = tk.Button(janela, text="Salvar Edição", command=registrar_producao)
btn_salvar_edicao.pack_forget()

btn_backup = tk.Button(janela, text="Fazer Backup", command=fazer_backup)
btn_backup.pack(pady=5)

# Criar as tabelas no banco de dados (se não existirem)
criar_tabela_pas()
criar_tabela_producao()

# Iniciar a interface gráfica
janela.mainloop()