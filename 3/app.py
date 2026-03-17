import flet as ft
import hashlib
import json
import time
import threading

from contracts import Transaction, do_all_transactions_one_block


# -----------------------------
# Твой блок (почти как у тебя), только data может быть список транзакций
# -----------------------------
class Block:  # класс блок самый главный
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):  # __init__ автоматический запуск при создании объекта
        self.index = index  # селф указание что ИМЕННО ЭТОТ БЛОК
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce  # кто не шарит тот не шарит
        self.hash = self.calculate_hash()  # hash это цифровой отпечаток блока типа отпечаток как на пальцах

    def calculate_hash(self):  # все поля блока собираем в один
        # json.dumps не умеет сериализовать объекты Transaction, поэтому делаем список dict
        if type(self.data) is list:
            tx_data = []
            for tx in self.data:
                tx_data.append({
                    "from": tx.frm,
                    "to": tx.to,
                    "amount": tx.amount,
                    "payload": tx.payload
                })
            data_for_hash = tx_data
        else:
            data_for_hash = self.data

        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": data_for_hash,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }

        block_string = json.dumps(block_data, sort_keys=True, ensure_ascii=False).encode()
        return hashlib.sha256(block_string).hexdigest()

    # майнинг сделаем функцией для UI (чтобы можно было обновлять nonce/hash)
    def mine_step(self):
        self.hash = self.calculate_hash()
        if self.hash.startswith("0" * self._difficulty):
            return True
        self.nonce += 1
        return False

    def mine_with_visual(self, difficulty, on_update, stop_flag):
        self._difficulty = difficulty
        self.nonce = 0

        # обновляем UI не на каждом шаге, а раз в N итераций
        tick = 0
        while True:
            if stop_flag["stop"]:
                return False  # прервали майнинг

            done = self.mine_step()
            tick += 1

            if tick % 2000 == 0:
                on_update(self.nonce, self.hash)

            if done:
                on_update(self.nonce, self.hash)
                return True


# -----------------------------
# "Blockchainik": хранит chain + balances + logs
# -----------------------------
class Blockchainik:
    def __init__(self, difficulty, genesis_state):
        self.difficulty = difficulty
        self.state = dict(genesis_state)
        self.chain = []
        self.logs = []

        genesis = Block(0, time.time(), [], "0")
        genesis.nonce = 0
        genesis._difficulty = difficulty
        # “быстро” замайним генезис без визуалки
        while not genesis.calculate_hash().startswith("0" * difficulty):
            genesis.nonce += 1
        genesis.hash = genesis.calculate_hash()

        self.chain.append(genesis)
        self.logs.append("GENESIS: state=" + str(self.state))

    def last_hash(self):
        return self.chain[-1].hash


# -----------------------------
# Flet UI
# -----------------------------
def main(page: ft.Page):
    page.title = "LR3 + Flet: Smart Contract Blockchain"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 800
    page.padding = 20

    # состояние приложения
    bc = Blockchainik(
        difficulty=3,
        genesis_state={"Alice": 100, "Bob": 40, "Charlie": 10}
    )
    pending_txs = []  # транзакции, которые сейчас собираем в "будущий блок"
    stop_mining = {"stop": False}

    # ---------------- UI элементы ----------------

    # Балансы
    bal_alice = ft.Text()
    bal_bob = ft.Text()
    bal_charlie = ft.Text()

    def refresh_balances():
        bal_alice.value = f"Alice: {bc.state.get('Alice', 0)}"
        bal_bob.value = f"Bob: {bc.state.get('Bob', 0)}"
        bal_charlie.value = f"Charlie: {bc.state.get('Charlie', 0)}"
        page.update()

    balances_card = ft.Card(
        content=ft.Container(
            padding=15,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("Balances", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE), bal_alice]),
                    ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE), bal_bob]),
                    ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE), bal_charlie]),
                ],
            ),
        )
    )

    # Difficulty
    diff_text = ft.Text(value=f"Difficulty: {bc.difficulty}", size=14)

    def on_diff_change(e):
        bc.difficulty = int(diff_slider.value)
        diff_text.value = f"Difficulty: {bc.difficulty}"
        page.update()

    diff_slider = ft.Slider(
        min=1, max=5, divisions=4,
        value=bc.difficulty,
        label="{value}",
        on_change=on_diff_change
    )

    diff_card = ft.Card(
        content=ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Text("Mining difficulty", size=18, weight=ft.FontWeight.BOLD),
                    diff_text,
                    diff_slider,
                    ft.Text("Чем выше — тем дольше майнинг.", size=12, opacity=0.7)
                ]
            )
        )
    )

    # Форма добавления транзакции
    sender = ft.Dropdown(
        label="From",
        width=200,
        options=[ft.dropdown.Option("Alice"), ft.dropdown.Option("Bob"), ft.dropdown.Option("Charlie")],
        value="Alice"
    )
    receiver = ft.Dropdown(
        label="To",
        width=200,
        options=[ft.dropdown.Option("Alice"), ft.dropdown.Option("Bob"), ft.dropdown.Option("Charlie")],
        value="Bob"
    )
    amount = ft.TextField(label="Amount", width=200, value="10")
    use_contract = ft.Checkbox(label="Use contract (cond)", value=False)
    min_balance = ft.TextField(label="Min balance X (balance must be > X)", width=250, value="50", disabled=True)

    def on_contract_toggle(e):
        min_balance.disabled = not use_contract.value
        page.update()

    use_contract.on_change = on_contract_toggle

    # Список pending транзакций (UI)
    pending_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh_pending_list():
        pending_list.controls.clear()
        if not pending_txs:
            pending_list.controls.append(ft.Text("Нет транзакций. Добавь первую 👇", opacity=0.7))
        else:
            for i, tx in enumerate(pending_txs, start=1):
                payload_txt = "None" if tx.payload is None else str(tx.payload)
                pending_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=12,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"#{i}  {tx.frm} -> {tx.to}  amount={tx.amount}", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"payload={payload_txt}", size=12, opacity=0.8),
                                ],
                            )
                        )
                    )
                )
        page.update()

    def add_tx(e):
        # проверки ввода
        if sender.value is None or receiver.value is None:
            return

        try:
            amt = int(amount.value)
        except:
            show_snack("Amount должен быть числом")
            return

        payload = None
        if use_contract.value:
            try:
                x = int(min_balance.value)
            except:
                show_snack("Min balance должен быть числом")
                return
            payload = {"type": "cond", "min_balance": x}

        tx = Transaction(sender.value, receiver.value, amt, payload)
        pending_txs.append(tx)
        log_append(f"TX added: {tx.frm}->{tx.to} amount={tx.amount} payload={tx.payload}")
        refresh_pending_list()

    def clear_pending(e):
        pending_txs.clear()
        log_append("Pending txs cleared")
        refresh_pending_list()

    tx_form_card = ft.Card(
        content=ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Text("Create transaction", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([sender, receiver, amount], wrap=True),
                    ft.Row([use_contract, min_balance], wrap=True),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Add TX to block", icon=ft.Icons.ADD, on_click=add_tx),
                            ft.OutlinedButton("Clear pending", icon=ft.Icons.DELETE_OUTLINE, on_click=clear_pending),
                        ]
                    ),
                ],
            ),
        )
    )

    pending_card = ft.Card(
        content=ft.Container(
            padding=15,
            height=320,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text("Pending block transactions", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    pending_list
                ],
            ),
        )
    )

    # Логи
    log_box = ft.Text(selectable=True)
    log_view = ft.Container(
        padding=15,
        height=260,
        content=ft.Column(
            controls=[
                ft.Text("Execution log", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([log_box], scroll=ft.ScrollMode.AUTO, expand=True),
                    expand=True
                )
            ],
            expand=True
        )
    )

    def log_append(s):
        if log_box.value is None:
            log_box.value = ""
        log_box.value += ("" if log_box.value == "" else "\n") + s
        page.update()

    def show_snack(msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    # Цепочка блоков (UI)
    chain_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh_chain_view():
        chain_list.controls.clear()

        for b in bc.chain:
            tx_count = len(b.data) if type(b.data) is list else 0

            # список транзакций внутри Expander
            tx_lines = []
            if type(b.data) is list and b.data:
                for tx in b.data:
                    tx_lines.append(ft.Text(f"{tx.frm} -> {tx.to} amount={tx.amount} payload={tx.payload}", size=12))
            else:
                tx_lines.append(ft.Text("(no transactions)", size=12, opacity=0.7))

            chain_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(f"Block #{b.index}", size=16, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"txs: {tx_count}", size=12, opacity=0.8),
                                    ],
                                ),
                                ft.Text(f"hash: {b.hash}", size=12),
                                ft.Text(f"prev: {b.previous_hash}", size=12, opacity=0.8),
                                ft.ExpansionTile(
                                    title=ft.Text("Transactions inside block"),
                                    controls=tx_lines
                                ),
                            ]
                        )
                    )
                )
            )

        page.update()

    chain_card = ft.Card(
        content=ft.Container(
            padding=15,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text("Blockchain", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    chain_list
                ],
            ),
        )
    )

    # Майнинг визуализация
    mining_status = ft.Text(value="Mining status: idle", size=14)
    mining_nonce = ft.Text(value="nonce: -", size=12, opacity=0.8)
    mining_hash = ft.Text(value="hash: -", size=12, opacity=0.8)
    mining_bar = ft.ProgressBar(value=None)  # None = бесконечный индикатор
    mining_bar.visible = False

    mine_btn = ft.ElevatedButton("Mine + execute block", icon=ft.Icons.HARDWARE, disabled=False)
    stop_btn = ft.OutlinedButton("Stop mining", icon=ft.Icons.STOP, disabled=True)

    def on_mining_update(nonce, h):
        mining_nonce.value = f"nonce: {nonce}"
        mining_hash.value = f"hash: {h}"
        page.update()

    def stop_mine(e):
        stop_mining["stop"] = True
        stop_btn.disabled = True
        mining_status.value = "Mining status: stopping..."
        page.update()

    stop_btn.on_click = stop_mine

    def mine_and_execute(e):
        if not pending_txs:
            show_snack("Добавь хотя бы одну транзакцию в pending block")
            return

        # блокируем кнопки
        mine_btn.disabled = True
        stop_btn.disabled = False
        stop_mining["stop"] = False
        mining_bar.visible = True
        mining_status.value = "Mining status: mining..."
        mining_nonce.value = "nonce: 0"
        mining_hash.value = "hash: ..."
        page.update()

        # создаём блок-кандидат
        new_block = Block(len(bc.chain), time.time(), list(pending_txs), bc.last_hash(), nonce=0)

        def worker():
            # майним с визуализацией
            ok_mine = new_block.mine_with_visual(
                difficulty=bc.difficulty,
                on_update=lambda n, h: page.call_from_thread(lambda: on_mining_update(n, h)),
                stop_flag=stop_mining
            )

            def finish_ui():
                mining_bar.visible = False
                stop_btn.disabled = True
                mine_btn.disabled = False

                if not ok_mine:
                    mining_status.value = "Mining status: stopped"
                    page.update()
                    return

                mining_status.value = f"Mining status: mined! (difficulty={bc.difficulty})"
                page.update()

                # теперь выполняем транзакции блока с откатом
                bc.logs.append(f"\nBLOCK #{new_block.index} mined hash={new_block.hash[:10]}...")
                _, log_lines, ok_exec = do_all_transactions_one_block(bc.state, new_block.data)
                for line in log_lines:
                    bc.logs.append(line)

                if ok_exec:
                    bc.chain.append(new_block)
                    bc.logs.append("BLOCK ADDED, state=" + str(bc.state))
                    log_append(f"BLOCK #{new_block.index} ADDED ✅ state={bc.state}")
                    pending_txs.clear()
                    refresh_pending_list()
                    refresh_chain_view()
                    refresh_balances()
                else:
                    bc.logs.append("BLOCK REJECTED (ROLLBACK), state=" + str(bc.state))
                    log_append(f"BLOCK #{new_block.index} REJECTED ❌ (ROLLBACK) state={bc.state}")
                    refresh_balances()

            page.call_from_thread(finish_ui)

        threading.Thread(target=worker, daemon=True).start()

    mine_btn.on_click = mine_and_execute

    mining_card = ft.Card(
        content=ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Text("Mining visualization", size=18, weight=ft.FontWeight.BOLD),
                    mining_status,
                    mining_nonce,
                    mining_hash,
                    mining_bar,
                    ft.Row([mine_btn, stop_btn], wrap=True),
                    ft.Text("Подсказка: difficulty 4–5 может быть долго.", size=12, opacity=0.7)
                ]
            )
        )
    )

    # ---------------- Layout (колонки) ----------------
    left_col = ft.Column(
        expand=True,
        controls=[
            balances_card,
            diff_card,
            tx_form_card,
            pending_card,
            mining_card,
        ],
        spacing=12,
    )

    right_col = ft.Column(
        expand=True,
        controls=[
            chain_card,
            ft.Card(content=log_view),
        ],
        spacing=12,
    )

    page.add(
        ft.Row(
            controls=[left_col, right_col],
            expand=True,
            spacing=15,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
    )

    # первичная отрисовка
    refresh_balances()
    refresh_pending_list()
    refresh_chain_view()
    log_append("App started. Add TXs -> Mine + execute block.")


ft.app(target=main)