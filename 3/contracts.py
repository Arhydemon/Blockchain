class Transaction:
    def __init__(self, frm, to, amount, payload=None):
        self.frm = frm
        self.to = to
        self.amount = amount
        self.payload = payload

def apply_transaction(state, transaction):
    if transaction.frm not in state:
        return False, ("нет аккаунта отправителя: " + transaction.frm)
    
    if transaction.to not in state:
        return False, ("нет аккаунта получателя: " + transaction.to)
    
    if transaction.amount <= 0:
        return False, "amount должен быть > 0"
    
    if transaction.payload is None:
        if state[transaction.frm] < transaction.amount:
            return False, "не хватает денег у " + transaction.frm
        state[transaction.frm] -= transaction.amount
        state[transaction.to] += transaction.amount
        return True, f"Перевод выполнен {transaction.frm} --> {transaction.to} {transaction.amount}"
    
    if transaction.payload.get("type") == "cond":
        x = transaction.payload.get("min_balance", 0)

        if state[transaction.frm] <= x:
            return False, f"Условие не выполнено: баланс({transaction.frm})={state[transaction.frm]} <= {x}"
        
        if state[transaction.frm] < transaction.amount:
            return False, f"не хватает денег у {transaction.frm}"
        
        state[transaction.frm] -= transaction.amount
        state[transaction.to] += transaction.amount
        return True, f"Контракт выполнен: {transaction.frm} -> {transaction.to}, сумма {transaction.amount} (баланс больше {x})"
    
    return False, "Неизвестный контракт"

def do_all_transactions_one_block(state, transaction_list):
    snapshot = dict(state)
    log = []

    for i, tx in enumerate(transaction_list, start=1):
        ok, msg = apply_transaction(state, tx)
        log.append(f"транзакция {i}: {msg}")
        if not ok:
            state.clear()
            state.update(snapshot)
            log.append("состояние восстановлено")
            return state, log, False

    log.append("все транзакции применены")
    return state, log, True