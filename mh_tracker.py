import json
import re
import sqlite3
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from pathlib import Path
from datetime import datetime
import locale

# Attempt Portuguese locale setting for dates if available
try:
    locale.setlocale(locale.LC_ALL, "pt_PT.UTF-8")
except Exception:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Portugal.1252")
    except Exception:
        pass

DB_FILE = "monster_high_inventory.db"

# Color Palette - Monster High Dark Velvet Theme
COLOR_BG_DARK = "#120D16"
COLOR_CARD_BG = "#1C1524"
COLOR_CARD_BORDER = "#30223D"
COLOR_HEADER_BG = "#271B33"
COLOR_PINK_NEON = "#FF007F"
COLOR_PURPLE_ELECTRIC = "#9C27B0"
COLOR_CYAN_MINT = "#00F5D4"
COLOR_GOLD = "#FFC107"
COLOR_TEXT_WHITE = "#FFFFFF"
COLOR_TEXT_MUTED = "#B3A4C4"

STATUS_MAP = {
    "in_stock": "Em Stock 🟢",
    "sold": "Vendido 🔵",
    "personal": "Coleção Própria 🟣"
}

STATUS_REVERSE_MAP = {
    "Em Stock 🟢": "in_stock",
    "In Stock": "in_stock",
    "Vendido 🔵": "sold",
    "Sold": "sold",
    "Coleção Própria 🟣": "personal",
    "Personal": "personal"
}

COLLECTIONS = (
    "Not Known",
    "13 Wishes",
    "Boo York, Boo York",
    "Budget Dolls",
    "Create-A-Monster",
    "Creeproduction",
    "Dead Tired",
    "Dot Dead Gorgeous",
    "Fang Vote",
    "Fashion Pack",
    "Freak Du Chic",
    "Freaky Fusion",
    "Ghoul Sports",
    "Ghouls Alive!",
    "Ghouls Rule!",
    "Gloom Beach",
    "Great Scarrier Reef",
    "Haunted",
    "I <3 Fashion",
    "Jinafire Long",
    "Killer Style",
    "Maul Monsteristas",
    "Monster Exchange",
    "Monster Fest",
    "New Scaremester",
    "Party",
    "Picture Day",
    "Power Ghouls",
    "Roller Maze",
    "Scare-itage Collection",
    "Scaris: City of Frights",
    "School's Out",
    "Shriekwrecked",
    "Signature (G1)",
    "Signature (G3)",
    "Skull Shores",
    "Skullector",
    "Skultimate Roller Maze",
    "Sweet 1600",
    "Voltageous",
    "Weird Science",
    "Other",
)

CONDITIONS = ("NIB", "Excellent", "Good", "To be restored")
COMPLETENESS = ("Complete", "Incomplete")

DOLL_COLUMNS = """
    id,
    name,
    character_name,
    line,
    condition,
    completeness,
    purchase_price,
    purchase_date,
    selling_price,
    platform_fee,
    shipping_cost,
    restoration_cost,
    sold_date,
    status,
    notes,
    sold_price,
    batch_id,
    estimated_market_value
"""


def _split_character_names(raw_character):
    text = (raw_character or "").strip()
    if not text:
        return []

    parts = re.split(r"\s*(?:,|&| and | with )\s*", text, flags=re.IGNORECASE)
    names = []
    for part in parts:
        candidate = part.strip(" -–")
        if not candidate or candidate.lower() in {"and", "with"}:
            continue
        if candidate not in names:
            names.append(candidate)
    return names or [text]


def _build_catalog_rows(collection, character, line_name, notes, source_title=None):
    names = _split_character_names(character)
    if not names:
        return []
    if len(names) == 1:
        return [(collection, names[0], line_name, source_title or line_name, "🧟", notes)]
    display_line = f"{line_name} — {' & '.join(names)}" if line_name else " & ".join(names)
    return [(collection, name, display_line, source_title or display_line, "🧟", notes) for name in names]


def _parse_catalog_text(text):
    collection_names = {"SIGNATURE", "BUDGET", "DELUXE", "COLLECTOR", "SDCC", "ALTER-SIZE", "OTHER"}

    def is_year_line(value):
        if not value:
            return False
        return bool(re.fullmatch(r"\d{4}s?|\d{4}–\d{4}", value.strip()))

    def parse_block(block):
        if len(block) < 3:
            return []
        collection = block[0].strip()
        body = [line.strip() for line in block[1:] if line.strip()]
        if len(body) == 2:
            line_name, character, notes = body[0], body[1], ""
        elif len(body) == 3:
            if is_year_line(body[2]):
                line_name, character, notes = body[0], body[1], body[2]
            else:
                line_name, character, notes = f"{body[0]} — {body[1]}", body[2], ""
        else:
            if is_year_line(body[-1]):
                line_name = " — ".join(body[:-2]) if len(body) > 3 else body[0]
                character, notes = body[-2], body[-1]
            else:
                line_name = " — ".join(body[:-1])
                character, notes = body[-1], ""

        if not collection or not character:
            return []
        return _build_catalog_rows(collection, character, line_name, notes)

    blocks, current_block = [], []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue
        if line.upper() in collection_names and current_block:
            blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    rows = []
    for block in blocks:
        parsed_rows = parse_block(block)
        if parsed_rows:
            rows.extend(parsed_rows)
    return rows


def _load_catalog_from_file(c):
    c.execute("DELETE FROM catalog_dolls")
    catalog_files = [
        Path("ghouls_catalog_data.txt"),
        Path("ghouls_catalog.json"),
        Path("ghouls_catalog_sample.json"),
    ]

    for catalog_file in catalog_files:
        if not catalog_file.exists():
            continue

        if catalog_file.suffix.lower() == ".json":
            try:
                with catalog_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                continue

            if isinstance(data, list):
                rows = []
                for item in data:
                    character = (item.get("character") or "").strip()
                    if not character:
                        continue

                    for release in item.get("releases", []):
                        title = str(release or "").strip()
                        if not title:
                            continue

                        cleaned = re.sub(r"\s*\((?:B|E|R|\d{4})\)", "", title)
                        cleaned = re.sub(r"\s*\(\d{4}\)", "", cleaned).strip(" -–")

                        collection = "Other"
                        character_names = _split_character_names(character)
                        primary_character = character_names[0] if character_names else character
                        if primary_character.lower() in cleaned.lower():
                            idx = cleaned.lower().find(primary_character.lower())
                            prefix = cleaned[:idx].strip(" -–")
                            if prefix and prefix.lower() not in {"monster high"}:
                                collection = prefix

                        doll_name = cleaned or character
                        rows.extend(_build_catalog_rows(collection, character, doll_name, title, title))

                if rows:
                    c.executemany(
                        """
                        INSERT INTO catalog_dolls (collection, character, doll_name, variant, image_emoji, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                    return
        else:
            try:
                text = catalog_file.read_text(encoding="utf-8")
            except Exception:
                continue

            rows = _parse_catalog_text(text)
            if rows:
                c.executemany(
                    """
                    INSERT INTO catalog_dolls (collection, character, doll_name, variant, image_emoji, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                return


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS dolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            character_name TEXT,
            line TEXT,
            condition TEXT,
            completeness TEXT,
            purchase_price REAL,
            purchase_date TEXT,
            selling_price REAL,
            sold_price REAL,
            platform_fee REAL,
            shipping_cost REAL,
            restoration_cost REAL,
            sold_date TEXT,
            status TEXT DEFAULT 'in_stock',
            notes TEXT,
            batch_id TEXT,
            estimated_market_value REAL
        )
        """
    )
    c.execute("PRAGMA table_info(dolls)")
    doll_columns = {row[1] for row in c.fetchall()}

    if "sold_price" not in doll_columns:
        c.execute("ALTER TABLE dolls ADD COLUMN sold_price REAL")
        c.execute("UPDATE dolls SET sold_price = selling_price WHERE status = 'sold' AND sold_price IS NULL")

    if "batch_id" not in doll_columns:
        c.execute("ALTER TABLE dolls ADD COLUMN batch_id TEXT")

    if "estimated_market_value" not in doll_columns:
        c.execute("ALTER TABLE dolls ADD COLUMN estimated_market_value REAL")

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_dolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection TEXT NOT NULL,
            character TEXT NOT NULL,
            doll_name TEXT NOT NULL,
            variant TEXT,
            image_emoji TEXT,
            notes TEXT
        )
        """
    )
    conn.commit()

    c.execute("SELECT COUNT(*) FROM catalog_dolls")
    catalog_files = [Path("ghouls_catalog.json"), Path("ghouls_catalog_data.txt"), Path("ghouls_catalog_sample.json")]
    if c.fetchone()[0] == 0 or any(path.exists() for path in catalog_files):
        _load_catalog_from_file(c)
        conn.commit()

    conn.close()


def data_para_iso(data_pt):
    if not data_pt:
        return None
    text = str(data_pt).strip()
    if not text:
        return None
    try:
        dia, mes, ano = text.split("/")
        return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
    except ValueError:
        return text


def iso_para_data(iso):
    if not iso:
        return ""
    text = str(iso).strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        ano, mes, dia = text.split("-")
        return f"{dia}/{mes}/{ano}"
    return text


def hoje_pt():
    return datetime.now().strftime("%d/%m/%Y")


def limpar_preco(valor):
    if valor is None:
        return 0.0
    text = str(valor).strip()
    if not text:
        return 0.0
    text = re.sub(r"[^\d,.-]", "", text)
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def limpar_preco_opcional(valor):
    if valor is None or str(valor).strip() == "":
        return None
    return limpar_preco(valor)


def split_missing_notes(notes):
    text = notes or ""
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("missing:"):
        return lines[0].split(":", 1)[1].strip(), "\n".join(lines[1:]).strip()
    return "", text.strip()


def combine_missing_notes(completeness, missing, notes):
    clean_notes = (notes or "").strip()
    clean_missing = (missing or "").strip()
    if completeness == "Incomplete" and clean_missing:
        return f"Missing: {clean_missing}" if not clean_notes else f"Missing: {clean_missing}\n{clean_notes}"
    return clean_notes


class MHApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Monster High Stock & Collection Manager 🧟‍♀️")
        self.geometry("1300x840")
        self.minsize(1100, 700)
        self.configure(fg_color=COLOR_BG_DARK)

        init_db()

        self.sort_column = "id"
        self.sort_reverse = False

        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        # Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_HEADER_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        self.header_frame.pack(fill="x", padx=16, pady=(14, 8))

        header_title = ctk.CTkLabel(
            self.header_frame,
            text="🧟‍♀️ MONSTER HIGH INVENTORY & COLLECTION 🧟‍♀️",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_PINK_NEON
        )
        header_title.pack(anchor="w", padx=20, pady=(12, 4))

        # KPI Dashboard Cards Frame
        self.kpi_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.kpi_frame.pack(fill="x", padx=16, pady=(4, 12))
        self.kpi_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        # KPI 1: Personal Collection
        self.kpi1_card = ctk.CTkFrame(self.kpi_frame, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_PURPLE_ELECTRIC)
        self.kpi1_card.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(self.kpi1_card, text="🟣 Coleção Própria", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PURPLE_ELECTRIC).pack(anchor="w", padx=12, pady=(8, 2))
        self.kpi1_value = ctk.CTkLabel(self.kpi1_card, text="0 itens", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_WHITE)
        self.kpi1_value.pack(anchor="w", padx=12, pady=0)
        self.kpi1_sub = ctk.CTkLabel(self.kpi1_card, text="Custo Efetivo: €0.00", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.kpi1_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # KPI 2: Inventory in Stock
        self.kpi2_card = ctk.CTkFrame(self.kpi_frame, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CYAN_MINT)
        self.kpi2_card.grid(row=0, column=1, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(self.kpi2_card, text="🟢 Em Stock (Revenda)", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_CYAN_MINT).pack(anchor="w", padx=12, pady=(8, 2))
        self.kpi2_value = ctk.CTkLabel(self.kpi2_card, text="0 itens", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_WHITE)
        self.kpi2_value.pack(anchor="w", padx=12, pady=0)
        self.kpi2_sub = ctk.CTkLabel(self.kpi2_card, text="Investimento: €0.00", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.kpi2_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # KPI 3: Realized Resale Profit
        self.kpi3_card = ctk.CTkFrame(self.kpi_frame, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_GOLD)
        self.kpi3_card.grid(row=0, column=2, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(self.kpi3_card, text="💰 Lucro de Revenda", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        self.kpi3_value = ctk.CTkLabel(self.kpi3_card, text="€0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_GOLD)
        self.kpi3_value.pack(anchor="w", padx=12, pady=0)
        self.kpi3_sub = ctk.CTkLabel(self.kpi3_card, text="0 itens vendidos", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.kpi3_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # KPI 4: Collection Amortization %
        self.kpi4_card = ctk.CTkFrame(self.kpi_frame, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_PINK_NEON)
        self.kpi4_card.grid(row=0, column=3, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(self.kpi4_card, text="🧮 Absorção de Custos", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PINK_NEON).pack(anchor="w", padx=12, pady=(8, 2))
        self.kpi4_value = ctk.CTkLabel(self.kpi4_card, text="0%", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_WHITE)
        self.kpi4_value.pack(anchor="w", padx=12, pady=0)
        self.kpi4_sub = ctk.CTkLabel(self.kpi4_card, text="Custo Coleção Amortizado", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.kpi4_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # Action Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=4)

        buttons = [
            ("➕ Adicionar", self.add_doll, COLOR_PURPLE_ELECTRIC),
            ("📦 Compra Lote", self.batch_purchase_dialog, COLOR_PINK_NEON),
            ("✏️ Editar", self.edit_doll, "#7B1FA2"),
            ("💰 Vender", self.sell_doll, "#E67E22"),
            ("🟣 Coleção Própria", self.move_to_personal, "#8E24AA"),
            ("🧮 Calculadora Lote", self.amortization_calculator_dialog, COLOR_CYAN_MINT),
            ("📊 Dashboard", self.dashboard, "#2ECC71"),
            ("📁 Exportar CSV", self.export_csv, "#1ABC9C"),
            ("🗑️ Eliminar", self.delete_doll, "#E74C3C"),
            ("🔄 Atualizar", self.refresh_table, "#7F8C8D"),
        ]

        for text, cmd, color in buttons:
            btn = ctk.CTkButton(
                toolbar,
                text=text,
                command=cmd,
                fg_color=color,
                hover_color=self._adjust_color_brightness(color, 0.85),
                font=ctk.CTkFont(size=11, weight="bold"),
                height=32,
                corner_radius=8
            )
            btn.pack(side="left", padx=3)

        # Filter & Search Bar
        filter_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        filter_frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(filter_frame, text="Estado:", text_color=COLOR_TEXT_WHITE, font=ctk.CTkFont(size=12)).pack(side="left", padx=(12, 4), pady=8)
        self.filter_status_var = ctk.StringVar(value="Todos")
        self.status_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.filter_status_var,
            values=["Todos", "Em Stock 🟢", "Vendido 🔵", "Coleção Própria 🟣"],
            command=lambda _v: self.refresh_table(),
            width=150,
            fg_color=COLOR_HEADER_BG,
            button_color=COLOR_PURPLE_ELECTRIC
        )
        self.status_dropdown.pack(side="left", padx=4)

        ctk.CTkLabel(filter_frame, text="Linha/Coleção:", text_color=COLOR_TEXT_WHITE, font=ctk.CTkFont(size=12)).pack(side="left", padx=(16, 4))
        self.filter_collection_var = ctk.StringVar(value="Todas")
        self.col_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.filter_collection_var,
            values=["Todas"] + list(COLLECTIONS),
            command=lambda _v: self.refresh_table(),
            width=180,
            fg_color=COLOR_HEADER_BG,
            button_color=COLOR_PURPLE_ELECTRIC
        )
        self.col_dropdown.pack(side="left", padx=4)

        ctk.CTkLabel(filter_frame, text="🔍 Pesquisa:", text_color=COLOR_TEXT_WHITE, font=ctk.CTkFont(size=12)).pack(side="left", padx=(16, 4))
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Pesquisar boneca, personagem...", width=220)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh_table())

        # Main Table View (Treeview inside Custom Frame)
        table_container = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        table_container.pack(fill="both", expand=True, padx=16, pady=4)

        scroll_y = ttk.Scrollbar(table_container, orient="vertical")
        scroll_x = ttk.Scrollbar(table_container, orient="horizontal")

        self.cols = (
            "ID",
            "Nome",
            "Personagem",
            "Linha",
            "Condição",
            "Completo",
            "Custo (€)",
            "Est. Venda (€)",
            "Vendido (€)",
            "Est. Mercado (€)",
            "Lucro / Custo Ef. (€)",
            "Comprado",
            "Vendido em",
            "Estado",
            "Lote ID"
        )

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#1B1424",
            foreground="#FFFFFF",
            rowheight=28,
            fieldbackground="#1B1424",
            bordercolor="#30223D",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background="#2A1B38",
            foreground="#FF007F",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Treeview", background=[("selected", "#8E24AA")], foreground=[("selected", "#FFFFFF")])

        self.tree = ttk.Treeview(
            table_container,
            columns=self.cols,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

        col_widths = [45, 180, 130, 130, 90, 90, 80, 90, 80, 100, 120, 85, 85, 120, 100]
        for index, col in enumerate(self.cols):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_tree(c))
            self.tree.column(col, width=col_widths[index], minwidth=40, anchor="center")

        # Row Tags for Dark Aesthetic
        self.tree.tag_configure("stock", background="#182A20", foreground="#69F0AE")
        self.tree.tag_configure("sold", background="#162338", foreground="#81D4FA")
        self.tree.tag_configure("personal", background="#2C1636", foreground="#FF80AB")

        self.tree.bind("<Double-1>", lambda _event: self.edit_doll())

        # Bottom Bar (Totals & Status)
        self.totals_bar = ctk.CTkLabel(
            self,
            text="Gasto Total: €0.00 | Lucro Real: €0.00 | Valor Coleção: €0.00",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
            fg_color=COLOR_HEADER_BG,
            corner_radius=8,
            height=30
        )
        self.totals_bar.pack(fill="x", padx=16, pady=(4, 10))

    def _adjust_color_brightness(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = [max(0, min(255, int(c * factor))) for c in rgb]
        return '#{:02x}{:02x}{:02x}'.format(*new_rgb)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        filtro_status_ui = self.filter_status_var.get()
        filtro_col = self.filter_collection_var.get()
        search_query = self.search_entry.get().strip().lower()

        query = f"SELECT {DOLL_COLUMNS} FROM dolls WHERE 1=1"
        params = []

        if filtro_status_ui != "Todos":
            status_code = STATUS_REVERSE_MAP.get(filtro_status_ui)
            if status_code:
                query += " AND status = ?"
                params.append(status_code)

        if filtro_col != "Todas":
            query += " AND line = ?"
            params.append(filtro_col)

        if search_query:
            query += " AND (LOWER(name) LIKE ? OR LOWER(character_name) LIKE ? OR LOWER(batch_id) LIKE ?)"
            term = f"%{search_query}%"
            params.extend([term, term, term])

        query += " ORDER BY status, name"
        c.execute(query, params)
        rows = c.fetchall()

        # Batch Amortization Calculations Map
        c.execute("SELECT id, purchase_price, platform_fee, shipping_cost, restoration_cost, status, sold_price, batch_id FROM dolls")
        all_dolls = c.fetchall()
        conn.close()

        # Group by batch_id
        batch_stats = {}
        for d in all_dolls:
            did, pur, fee, ship, rest, st, sold, b_id = d
            if not b_id:
                continue
            if b_id not in batch_stats:
                batch_stats[b_id] = {"total_cost": 0.0, "sold_revenue": 0.0, "personal_count": 0, "resale_count": 0}
            cost = (pur or 0) + (fee or 0) + (ship or 0) + (rest or 0)
            batch_stats[b_id]["total_cost"] += cost
            if st == "sold":
                batch_stats[b_id]["sold_revenue"] += (sold or 0) - (fee or 0)
            elif st == "personal":
                batch_stats[b_id]["personal_count"] += 1
            else:
                batch_stats[b_id]["resale_count"] += 1

        total_personal_items = 0
        total_personal_market_value = 0.0
        total_personal_effective_cost = 0.0
        total_stock_items = 0
        total_stock_cost = 0.0
        total_sold_items = 0
        total_sold_profit = 0.0
        total_spending = 0.0

        for row in rows:
            (
                did,
                name,
                char,
                line,
                cond,
                complete,
                purchase,
                pdate,
                selling,
                fee,
                shipping,
                restoration,
                sdate,
                status,
                notes,
                sold_price,
                batch_id,
                est_market
            ) = row

            total_cost = (purchase or 0) + (fee or 0) + (shipping or 0) + (restoration or 0)
            total_spending += total_cost

            # Effective cost & Profit calculations
            profit_str = "-"
            if status == "personal":
                total_personal_items += 1
                mkt_val = est_market or purchase or 0
                total_personal_market_value += mkt_val

                # Check if part of a batch with sales offsetting the cost
                if batch_id and batch_id in batch_stats:
                    b_info = batch_stats[batch_id]
                    # Resale revenue offsets personal item cost
                    eff_cost = max(0.0, total_cost - b_info["sold_revenue"])
                    profit_str = f"Eff: €{eff_cost:.2f}"
                    total_personal_effective_cost += eff_cost
                else:
                    profit_str = f"Eff: €{total_cost:.2f}"
                    total_personal_effective_cost += total_cost

            elif status == "sold":
                total_sold_items += 1
                net_profit = (sold_price or 0) - total_cost
                total_sold_profit += net_profit
                profit_str = f"+€{net_profit:.2f}" if net_profit >= 0 else f"-€{abs(net_profit):.2f}"
            else:  # in_stock
                total_stock_items += 1
                total_stock_cost += total_cost
                if selling:
                    est_profit = selling - total_cost
                    profit_str = f"Est: +€{est_profit:.2f}"

            tag = "personal" if status == "personal" else ("sold" if status == "sold" else "stock")
            status_disp = STATUS_MAP.get(status, "Em Stock 🟢")

            self.tree.insert(
                "",
                "end",
                values=(
                    did,
                    name,
                    char or "",
                    line or "",
                    cond or "",
                    complete or "",
                    f"€{purchase:.2f}" if purchase else "€0.00",
                    f"€{selling:.2f}" if selling else "-",
                    f"€{sold_price:.2f}" if sold_price else "-",
                    f"€{est_market:.2f}" if est_market else "-",
                    profit_str,
                    iso_para_data(pdate),
                    iso_para_data(sdate),
                    status_disp,
                    batch_id or "-"
                ),
                tags=(tag,)
            )

        # Update KPI Cards
        self.kpi1_value.configure(text=f"{total_personal_items} itens")
        self.kpi1_sub.configure(text=f"Custo Ef.: €{total_personal_effective_cost:.2f} | Mkt: €{total_personal_market_value:.2f}")

        self.kpi2_value.configure(text=f"{total_stock_items} itens")
        self.kpi2_sub.configure(text=f"Investimento: €{total_stock_cost:.2f}")

        self.kpi3_value.configure(text=f"€{total_sold_profit:.2f}")
        self.kpi3_sub.configure(text=f"{total_sold_items} itens vendidos")

        # Global Amortization %
        total_personal_raw_cost = sum((r[6] or 0) for r in rows if r[13] == 'personal')
        amort_pct = 0.0
        if total_personal_raw_cost > 0:
            offset = max(0.0, total_personal_raw_cost - total_personal_effective_cost)
            amort_pct = (offset / total_personal_raw_cost) * 100.0

        self.kpi4_value.configure(text=f"{amort_pct:.1f}%")

        self.totals_bar.configure(
            text=(
                f"Gasto Total em Stock: €{total_spending:.2f} | "
                f"Lucro Realizado: €{total_sold_profit:.2f} | "
                f"Coleção (Valor Mercado): €{total_personal_market_value:.2f} | "
                f"Coleção (Custo Real Ef.): €{total_personal_effective_cost:.2f}"
            )
        )

    def sort_tree(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False

        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(key=lambda x: x[0].lower() if isinstance(x[0], str) else x[0], reverse=self.sort_reverse)
        for index, (_, item_id) in enumerate(items):
            self.tree.move(item_id, "", index)

    def _get_catalog_characters(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT DISTINCT character FROM catalog_dolls WHERE character IS NOT NULL AND character != '' ORDER BY character")
        rows = [row[0] for row in c.fetchall()]
        conn.close()
        return rows or ["Unknown"]

    def _get_catalog_rows_by_character(self, character):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT collection, character, doll_name, variant, image_emoji, notes FROM catalog_dolls WHERE character = ? ORDER BY collection, doll_name",
            (character,)
        )
        rows = c.fetchall()
        conn.close()
        return rows

    # --- ACTION METHODS & DIALOGS ---

    def move_to_personal(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Por favor selecione uma boneca da tabela.")
            return

        item_id = self.tree.item(selected[0])["values"][0]

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE dolls SET status = 'personal', selling_price = 0 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso 🟣", f"Boneca ID {item_id} movida para Coleção Própria com Preço de Venda = €0.00.")
        self.refresh_table()

    def batch_purchase_dialog(self):
        """Dialog to create a multi-unit batch purchase with cost absorption calculator"""
        win = ctk.CTkToplevel(self)
        win.title("📦 Compra em Lote & Absorção de Custos")
        win.geometry("620x720")
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="📦 Registar Compra em Lote (Multi-Unidades)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_PINK_NEON
        ).pack(anchor="w", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            win,
            text="Comprei várias bonecas juntas? O app calcula automaticamente o preço ideal de revenda para a sua boneca ficar a 0€!",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED,
            wraplength=560
        ).pack(anchor="w", padx=20, pady=(0, 12))

        form = ctk.CTkFrame(win, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        form.pack(fill="both", expand=True, padx=20, pady=8)

        # Character / Name
        ctk.CTkLabel(form, text="Personagem / Modelo:").grid(row=0, column=0, sticky="w", padx=12, pady=8)
        char_entry = ctk.CTkEntry(form, placeholder_text="Ex: Frankie Stein Creeproduction", width=320)
        char_entry.grid(row=0, column=1, padx=12, pady=8)

        # Line / Collection
        ctk.CTkLabel(form, text="Linha/Coleção:").grid(row=1, column=0, sticky="w", padx=12, pady=8)
        line_dropdown = ctk.CTkOptionMenu(form, values=list(COLLECTIONS), width=320)
        line_dropdown.grid(row=1, column=1, padx=12, pady=8)

        # Total Units
        ctk.CTkLabel(form, text="Total de Unidades Compradas:").grid(row=2, column=0, sticky="w", padx=12, pady=8)
        units_entry = ctk.CTkEntry(form, width=100)
        units_entry.insert(0, "3")
        units_entry.grid(row=2, column=1, sticky="w", padx=12, pady=8)

        # Personal Units
        ctk.CTkLabel(form, text="Unidades para Coleção Própria 🟣:").grid(row=3, column=0, sticky="w", padx=12, pady=8)
        personal_entry = ctk.CTkEntry(form, width=100)
        personal_entry.insert(0, "1")
        personal_entry.grid(row=3, column=1, sticky="w", padx=12, pady=8)

        # Total Cost
        ctk.CTkLabel(form, text="Custo Total da Compra (€):").grid(row=4, column=0, sticky="w", padx=12, pady=8)
        cost_entry = ctk.CTkEntry(form, placeholder_text="Ex: 90.00", width=160)
        cost_entry.grid(row=4, column=1, sticky="w", padx=12, pady=8)

        # Total Shipping/Fees
        ctk.CTkLabel(form, text="Portes / Taxas Totais (€):").grid(row=5, column=0, sticky="w", padx=12, pady=8)
        shipping_entry = ctk.CTkEntry(form, placeholder_text="Ex: 6.00", width=160)
        shipping_entry.insert(0, "0")
        shipping_entry.grid(row=5, column=1, sticky="w", padx=12, pady=8)

        # Date
        ctk.CTkLabel(form, text="Data de Compra (DD/MM/AAAA):").grid(row=6, column=0, sticky="w", padx=12, pady=8)
        date_entry = ctk.CTkEntry(form, width=160)
        date_entry.insert(0, hoje_pt())
        date_entry.grid(row=6, column=1, sticky="w", padx=12, pady=8)

        # Calculation Live Result Frame
        res_card = ctk.CTkFrame(win, fg_color=COLOR_HEADER_BG, corner_radius=10, border_width=1, border_color=COLOR_PINK_NEON)
        res_card.pack(fill="x", padx=20, pady=10)

        res_label = ctk.CTkLabel(
            res_card,
            text="Preencha os campos e clique em 'Calcular Absorção'",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_CYAN_MINT,
            wraplength=540
        )
        res_label.pack(padx=14, pady=12)

        def do_calculate():
            try:
                tot_units = int(units_entry.get().strip())
                pers_units = int(personal_entry.get().strip())
                resale_units = tot_units - pers_units
                tot_cost = limpar_preco(cost_entry.get()) + limpar_preco(shipping_entry.get())

                if tot_units <= 0 or pers_units < 0 or resale_units < 0:
                    messagebox.showerror("Erro", "Valores de unidades inválidos.")
                    return None

                unit_cost = tot_cost / tot_units
                target_resale_price = (tot_cost / resale_units) if resale_units > 0 else 0.0

                res_label.configure(
                    text=(
                        f"📊 Análise do Lote:\n"
                        f"• Custo Unitário: €{unit_cost:.2f} / boneca\n"
                        f"• Custo Inicial Coleção: €{unit_cost * pers_units:.2f} ({pers_units}x)\n"
                        f"🎯 PREÇO RECOMENDADO DE REVENDA: €{target_resale_price:.2f} / unidade\n"
                        f"*(Ao vender as {resale_units} unidades a €{target_resale_price:.2f}, a sua boneca fica a 0.00€!)*"
                    )
                )
                return {
                    "tot_units": tot_units,
                    "pers_units": pers_units,
                    "resale_units": resale_units,
                    "unit_cost": unit_cost,
                    "target_resale_price": target_resale_price,
                    "tot_cost": tot_cost
                }
            except Exception as e:
                messagebox.showerror("Erro", f"Por favor verifique os números introduzidos.\n{e}")
                return None

        def save_batch():
            calc = do_calculate()
            if not calc:
                return

            char_name = char_entry.get().strip() or "Monster High Doll"
            line = line_dropdown.get()
            pdate = data_para_iso(date_entry.get().strip())
            batch_id = f"LOTE-{datetime.now().strftime('%Y%m%d-%H%M')}"

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            # Insert Personal Items
            for i in range(calc["pers_units"]):
                c.execute(
                    f"INSERT INTO dolls (name, character_name, line, condition, completeness, purchase_price, purchase_date, selling_price, status, batch_id, estimated_market_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{char_name} (Coleção)",
                        char_name,
                        line,
                        "Excellent",
                        "Complete",
                        calc["unit_cost"],
                        pdate,
                        0.0,
                        "personal",
                        batch_id,
                        calc["unit_cost"]
                    )
                )

            # Insert Resale Items
            for i in range(calc["resale_units"]):
                c.execute(
                    f"INSERT INTO dolls (name, character_name, line, condition, completeness, purchase_price, purchase_date, selling_price, status, batch_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{char_name} (Revenda #{i+1})",
                        char_name,
                        line,
                        "Excellent",
                        "Complete",
                        calc["unit_cost"],
                        pdate,
                        calc["target_resale_price"],
                        "in_stock",
                        batch_id
                    )
                )

            conn.commit()
            conn.close()

            messagebox.showinfo("Sucesso! 📦", f"Lote criado com sucesso ({batch_id})!\n{calc['pers_units']}x Coleção Própria + {calc['resale_units']}x Revenda adicionadas.")
            win.destroy()
            self.refresh_table()

        btn_calc = ctk.CTkButton(win, text="🧮 Calcular Preço Alvo", command=do_calculate, fg_color=COLOR_CYAN_MINT, text_color="#000000", font=ctk.CTkFont(weight="bold"))
        btn_calc.pack(padx=20, pady=4)

        btn_save = ctk.CTkButton(win, text="💾 Criar Lote na Base de Dados", command=save_batch, fg_color=COLOR_PINK_NEON, font=ctk.CTkFont(weight="bold"), height=38)
        btn_save.pack(padx=20, pady=(6, 16))

    def amortization_calculator_dialog(self):
        """Amortization lot breakdown and profit analyzer"""
        win = ctk.CTkToplevel(self)
        win.title("🧮 Calculadora de Absorção de Custos de Coleção")
        win.geometry("700x600")
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="🧮 Absorção de Custos & Rentabilidade de Lotes",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_CYAN_MINT
        ).pack(anchor="w", padx=20, pady=(16, 6))

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT DISTINCT batch_id FROM dolls WHERE batch_id IS NOT NULL AND batch_id != ''")
        batches = [r[0] for r in c.fetchall()]
        conn.close()

        if not batches:
            ctk.CTkLabel(win, text="Nenhum lote com ID registado ainda. Use o botão '📦 Compra Lote' para criar lotes agrupados!").pack(padx=20, pady=40)
            return

        batch_var = ctk.StringVar(value=batches[0])

        top_f = ctk.CTkFrame(win, fg_color="transparent")
        top_f.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(top_f, text="Selecionar Lote:").pack(side="left", padx=6)
        b_dd = ctk.CTkOptionMenu(top_f, variable=batch_var, values=batches, width=220)
        b_dd.pack(side="left", padx=6)

        card = ctk.CTkFrame(win, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="both", expand=True, padx=20, pady=10)

        info_label = ctk.CTkLabel(card, text="", justify="left", font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_WHITE)
        info_label.pack(padx=20, pady=20, fill="both", expand=True)

        def update_info(*args):
            b_id = batch_var.get()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(f"SELECT {DOLL_COLUMNS} FROM dolls WHERE batch_id = ?", (b_id,))
            rows = c.fetchall()
            conn.close()

            total_spent = 0.0
            personal_items = []
            resale_sold = []
            resale_unsold = []

            for r in rows:
                cost = (r[6] or 0) + (r[9] or 0) + (r[10] or 0) + (r[11] or 0)
                total_spent += cost
                if r[13] == "personal":
                    personal_items.append((r[1], cost))
                elif r[13] == "sold":
                    resale_sold.append((r[1], (r[15] or 0) - (r[9] or 0)))
                else:
                    resale_unsold.append((r[1], r[8] or 0))

            sold_rev = sum(s[1] for s in resale_sold)
            personal_cost = sum(p[1] for p in personal_items)
            effective_cost = max(0.0, personal_cost - sold_rev)
            amort_pct = (sold_rev / total_spent * 100.0) if total_spent > 0 else 0.0

            text_lines = [
                f"📦 ID do Lote: {b_id}",
                f"💰 Custo Total do Lote: €{total_spent:.2f}",
                f"🟣 Bonecas de Coleção ({len(personal_items)}x): Custo Inicial = €{personal_cost:.2f}",
                f"🔵 Unidades Vendidas ({len(resale_sold)}x): Receita = €{sold_rev:.2f}",
                f"🟢 Unidades em Stock ({len(resale_unsold)}x)",
                "--------------------------------------------------",
                f"📊 TAXA DE AMORTIZAÇÃO DO LOTE: {amort_pct:.1f}%",
                f"✨ Custo Efetivo Atual da sua Coleção: €{effective_cost:.2f}"
            ]

            if effective_cost == 0.0 and personal_cost > 0:
                profit_above = sold_rev - total_spent
                text_lines.append(f"🎉 PARABÉNS! A sua boneca de coleção ficou a 0.00€ (Lucro extra de +€{profit_above:.2f})!")

            info_label.configure(text="\n".join(text_lines))

        b_dd.configure(command=lambda _v: update_info())
        update_info()

    def add_doll(self):
        self._open_doll_dialog("Adicionar Nova Boneca")

    def edit_doll(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma boneca da tabela para editar.")
            return
        item_id = self.tree.item(selected[0])["values"][0]
        self._open_doll_dialog("Editar Boneca", edit_id=item_id)

    def _open_doll_dialog(self, title, edit_id=None):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("640x780")
        win.grab_set()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        existing_data = None
        if edit_id:
            c.execute(f"SELECT {DOLL_COLUMNS} FROM dolls WHERE id = ?", (edit_id,))
            existing_data = c.fetchone()

        ctk.CTkLabel(win, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_PINK_NEON).pack(anchor="w", padx=20, pady=(16, 10))

        form = ctk.CTkFrame(win, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        form.pack(fill="both", expand=True, padx=20, pady=8)

        # Fields
        ctk.CTkLabel(form, text="Nome da Boneca:").grid(row=0, column=0, sticky="w", padx=12, pady=6)
        name_entry = ctk.CTkEntry(form, width=320)
        name_entry.grid(row=0, column=1, padx=12, pady=6)

        ctk.CTkLabel(form, text="Personagem:").grid(row=1, column=0, sticky="w", padx=12, pady=6)
        char_entry = ctk.CTkEntry(form, width=320)
        char_entry.grid(row=1, column=1, padx=12, pady=6)

        ctk.CTkLabel(form, text="Linha/Coleção:").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        line_opt = ctk.CTkOptionMenu(form, values=list(COLLECTIONS), width=320)
        line_opt.grid(row=2, column=1, padx=12, pady=6)

        ctk.CTkLabel(form, text="Condição:").grid(row=3, column=0, sticky="w", padx=12, pady=6)
        cond_opt = ctk.CTkOptionMenu(form, values=list(CONDITIONS), width=180)
        cond_opt.grid(row=3, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Completude:").grid(row=4, column=0, sticky="w", padx=12, pady=6)
        comp_opt = ctk.CTkOptionMenu(form, values=list(COMPLETENESS), width=180)
        comp_opt.grid(row=4, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Estado:").grid(row=5, column=0, sticky="w", padx=12, pady=6)
        status_opt = ctk.CTkOptionMenu(form, values=["Em Stock 🟢", "Vendido 🔵", "Coleção Própria 🟣"], width=180)
        status_opt.grid(row=5, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Preço Compra (€):").grid(row=6, column=0, sticky="w", padx=12, pady=6)
        p_price_entry = ctk.CTkEntry(form, width=140)
        p_price_entry.grid(row=6, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Est. Venda (€):").grid(row=7, column=0, sticky="w", padx=12, pady=6)
        s_price_entry = ctk.CTkEntry(form, width=140)
        s_price_entry.grid(row=7, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Preço Vendido (€):").grid(row=8, column=0, sticky="w", padx=12, pady=6)
        sold_price_entry = ctk.CTkEntry(form, width=140)
        sold_price_entry.grid(row=8, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Val. Mercado Est. (€):").grid(row=9, column=0, sticky="w", padx=12, pady=6)
        mkt_entry = ctk.CTkEntry(form, width=140)
        mkt_entry.grid(row=9, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Lote ID:").grid(row=10, column=0, sticky="w", padx=12, pady=6)
        batch_entry = ctk.CTkEntry(form, width=180)
        batch_entry.grid(row=10, column=1, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(form, text="Notas:").grid(row=11, column=0, sticky="w", padx=12, pady=6)
        notes_entry = ctk.CTkEntry(form, width=320)
        notes_entry.grid(row=11, column=1, padx=12, pady=6)

        # Pre-fill data if edit
        if existing_data:
            (
                _id, name, char, line, cond, comp, pur, pdate, sell,
                fee, ship, rest, sdate, status, notes, sold, batch, mkt
            ) = existing_data

            name_entry.insert(0, name or "")
            char_entry.insert(0, char or "")
            if line in COLLECTIONS:
                line_opt.set(line)
            if cond in CONDITIONS:
                cond_opt.set(cond)
            if comp in COMPLETENESS:
                comp_opt.set(comp)

            status_opt.set(STATUS_MAP.get(status, "Em Stock 🟢"))
            p_price_entry.insert(0, str(pur) if pur is not None else "")
            s_price_entry.insert(0, str(sell) if sell is not None else "")
            sold_price_entry.insert(0, str(sold) if sold is not None else "")
            mkt_entry.insert(0, str(mkt) if mkt is not None else "")
            batch_entry.insert(0, batch or "")
            notes_entry.insert(0, notes or "")

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Erro", "O Nome da boneca é obrigatório.")
                return

            char = char_entry.get().strip()
            line = line_opt.get()
            cond = cond_opt.get()
            comp = comp_opt.get()
            st_code = STATUS_REVERSE_MAP.get(status_opt.get(), "in_stock")

            pur = limpar_preco_opcional(p_price_entry.get())
            sell = limpar_preco_opcional(s_price_entry.get())
            sold = limpar_preco_opcional(sold_price_entry.get())
            mkt = limpar_preco_opcional(mkt_entry.get())
            batch = batch_entry.get().strip() or None
            notes = notes_entry.get().strip() or None

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            if edit_id:
                c.execute(
                    """
                    UPDATE dolls SET
                        name = ?, character_name = ?, line = ?, condition = ?, completeness = ?,
                        purchase_price = ?, selling_price = ?, sold_price = ?, status = ?,
                        notes = ?, batch_id = ?, estimated_market_value = ?
                    WHERE id = ?
                    """,
                    (name, char, line, cond, comp, pur, sell, sold, st_code, notes, batch, mkt, edit_id)
                )
            else:
                c.execute(
                    """
                    INSERT INTO dolls (
                        name, character_name, line, condition, completeness,
                        purchase_price, purchase_date, selling_price, sold_price, status,
                        notes, batch_id, estimated_market_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, char, line, cond, comp, pur, data_para_iso(hoje_pt()), sell, sold, st_code, notes, batch, mkt)
                )

            conn.commit()
            conn.close()
            win.destroy()
            self.refresh_table()

        btn_save = ctk.CTkButton(win, text="💾 Guardar Boneca", command=save, fg_color=COLOR_PINK_NEON, font=ctk.CTkFont(weight="bold"), height=36)
        btn_save.pack(padx=20, pady=(10, 16))

    def sell_doll(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma boneca para marcar como vendida.")
            return

        item_id = self.tree.item(selected[0])["values"][0]

        win = ctk.CTkToplevel(self)
        win.title("💰 Marcar Boneca como Vendida")
        win.geometry("400x320")
        win.grab_set()

        ctk.CTkLabel(win, text="💰 Marcar como Vendida", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=20, pady=(16, 8))

        f = ctk.CTkFrame(win, fg_color=COLOR_CARD_BG, corner_radius=10)
        f.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(f, text="Preço de Venda Final (€):").pack(anchor="w", padx=14, pady=(12, 4))
        p_entry = ctk.CTkEntry(f, placeholder_text="Ex: 45.00", width=200)
        p_entry.pack(anchor="w", padx=14, pady=4)

        ctk.CTkLabel(f, text="Taxas de Plataforma Vinted/eBay (€):").pack(anchor="w", padx=14, pady=(12, 4))
        fee_entry = ctk.CTkEntry(f, placeholder_text="Ex: 2.50", width=200)
        fee_entry.insert(0, "0")
        fee_entry.pack(anchor="w", padx=14, pady=4)

        def confirm_sale():
            sold_p = limpar_preco(p_entry.get())
            fee_p = limpar_preco(fee_entry.get())

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(
                "UPDATE dolls SET status = 'sold', sold_price = ?, platform_fee = ?, sold_date = ? WHERE id = ?",
                (sold_p, fee_p, data_para_iso(hoje_pt()), item_id)
            )
            conn.commit()
            conn.close()

            win.destroy()
            self.refresh_table()
            messagebox.showinfo("Sucesso 💰", "Venda registada com sucesso!")

        ctk.CTkButton(win, text="Confirmar Venda", command=confirm_sale, fg_color=COLOR_GOLD, text_color="#000000", font=ctk.CTkFont(weight="bold")).pack(padx=20, pady=(0, 16))

    def dashboard(self):
        """Dashboard overview dialog"""
        win = ctk.CTkToplevel(self)
        win.title("📊 Dashboard de Performance & Rentabilidade")
        win.geometry("700x520")
        win.grab_set()

        ctk.CTkLabel(win, text="📊 Resumo Geral de Performance", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_PINK_NEON).pack(anchor="w", padx=20, pady=(16, 10))

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(f"SELECT {DOLL_COLUMNS} FROM dolls")
        rows = c.fetchall()
        conn.close()

        tot_invested = sum((r[6] or 0) for r in rows)
        sold_items = [r for r in rows if r[13] == 'sold']
        personal_items = [r for r in rows if r[13] == 'personal']
        stock_items = [r for r in rows if r[13] == 'in_stock']

        tot_profit = sum(((r[15] or 0) - (r[6] or 0) - (r[9] or 0)) for r in sold_items)
        personal_mkt = sum((r[17] or r[6] or 0) for r in personal_items)

        card = ctk.CTkFrame(win, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="both", expand=True, padx=20, pady=10)

        lines = [
            f"📦 Total de Bonecas Registadas: {len(rows)}",
            f"🟣 Na Coleção Própria: {len(personal_items)} itens",
            f"🟢 Em Stock para Venda: {len(stock_items)} itens",
            f"🔵 Vendidas: {len(sold_items)} itens",
            "--------------------------------------------------",
            f"💵 Investimento Total Efetuado: €{tot_invested:.2f}",
            f"💰 Lucro Líquido Acumulado de Vendas: €{tot_profit:.2f}",
            f"💎 Valor Total Estimado da Coleção Própria: €{personal_mkt:.2f}"
        ]

        ctk.CTkLabel(card, text="\n\n".join(lines), font=ctk.CTkFont(size=14), justify="left").pack(padx=24, pady=24)

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Ficheiros CSV", "*.csv"), ("Todos os Ficheiros", "*.*")],
            title="Exportar Inventário para CSV"
        )
        if not file_path:
            return

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(f"SELECT {DOLL_COLUMNS} FROM dolls")
        rows = c.fetchall()
        conn.close()

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Nome", "Personagem", "Linha", "Condicao", "Completude",
                "Preco_Compra", "Data_Compra", "Preco_Estimado_Venda", "Taxa_Plataforma",
                "Portes", "Restauracao", "Data_Venda", "Estado", "Notas", "Preco_Vendido",
                "Lote_ID", "Valor_Estimado_Mercado"
            ])
            writer.writerows(rows)

        messagebox.showinfo("Sucesso", f"Inventário exportado com sucesso para:\n{file_path}")

    def delete_doll(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma boneca da tabela para eliminar.")
            return

        item_id = self.tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirmar", f"Tem a certeza que pretende eliminar a boneca ID {item_id}?"):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM dolls WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()

            self.refresh_table()
            messagebox.showinfo("Eliminado", "Boneca eliminada com sucesso.")


if __name__ == "__main__":
    app = MHApp()
    app.mainloop()
