import hashlib # SHA-256 хеш
import json    # данные блока в строку
import time    # просто время
import copy    # чтобы делать копию состояния и откатывать если всё сломалось


class Transaction: # класс транзакции, тут хранится кто отправил, кому, сколько и какой прикол лежит в payload
    def __init__(self, from_addr, to_addr, amount, payload = None): # payload это типа доп инфа или команда для смарт контракта
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.amount = amount
        self.payload = payload if payload is not None else {}

    def to_dict(self): # превращаем транзакцию в словарь чтобы потом удобно хешировать блок
        return {
            "from": self.from_addr,
            "to": self.to_addr,
            "amount": self.amount,
            "payload": self.payload
        }


class Block: # класс блок самый главный
    def __init__(self, index, timestamp, transactions, previous_hash, nonce = 0): # теперь вместо data тут transactions
        self.index = index # селф указание что ИМЕННО ЭТОТ БЛОК
        self.timestamp = timestamp
        self.transactions = transactions # список транзакций внутри блока, теперь блок не пустышка а прям с движухой
        self.previous_hash = previous_hash
        self.nonce = nonce # кто не шарит тот не шарит, это число которое перебираем пока хеш не станет красивым
        self.hash = self.calculate_hash() # hash это цифровой отпечаток блока типа отпечаток как на пальцах

    def calculate_hash(self): # все поля блока собираем в один словарь
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions], # каждую транзакцию превращаем в словарь
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        # SHA-256 понимает только байты, .encode() превращает строку в байты
        # json.dumps превращает словарь в строку
        # sort_keys заставляет ключи идти в одном и том же порядке всегда
        # ensure_ascii = False чтобы русские буквы не корёжило в \u#####
        block_string = json.dumps(block_data, sort_keys = True, ensure_ascii = False).encode()
        return hashlib.sha256(block_string).hexdigest() # .hexdigest делает удобную строку из букв и цифр

    def mine(self, difficulty):
        target = "0" * difficulty # например если сложность 3 то надо чтобы хеш начинался на 000
        self.nonce = 0 # начинаем перебор с нуля

        while True: # тупо долбимся пока не добьёмся нужного хеша
            self.hash = self.calculate_hash()
            if self.hash[:difficulty] == target:
                break
            else:
                self.nonce += 1

    def drevo_merkle(self): # функция для расчёта корня дерева Мёркла, который позволяет быстро проверять наличие транзакции в блоке без необходимости перебирать все транзакции
        hashes = [
            hashlib.sha256(
                json.dumps(tx.to_dict(), sort_keys=True, ensure_ascii=False).encode() # превращаем транзакцию в строку и хешируем ее, так получаем лист дерева Мёркла, который зависит от всех транзакций в блоке
            ).hexdigest()
            for tx in self.transactions
        ] or [hashlib.sha256(b"HUI").hexdigest()]

        while len(hashes) > 1: # пока не останется один хеш, который и будет корнем дерева
            if len(hashes) % 2:
                hashes.append(hashes[-1])

            hashes = [
                hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(hashes), 2)
            ]

        return hashes[0] # единственный оставшийся хеш и есть корень дерева Мёркла, он зависит от всех транзакций в блоке и позволяет быстро проверять их целостность

class Blockchain: # отдельный класс блокчейна чтобы хранить и цепочку и состояние и логи
    def __init__(self, difficulty):
        self.difficulty = difficulty # сложность майнинга
        self.chain = [] # список где будут храниться ВСЕ блоки
        self.state = {} # состояние сети = балансы аккаунтов
        self.logs = [] # лог исполнения транзакций чтобы потом красиво показать что происходило

        # создаём генезис блок, это нулевой блок батя всей цепочки
        genesis = Block(0, time.time(), [], "0")
        genesis.mine(difficulty) # майним нулевой блок, чтобы он тоже был валидным
        self.chain.append(genesis)

    def proverka_merkla(self): # функция для проверки дерева Мёркла, просто выводим корни для каждого блока, если кто-то изменит транзакцию в блоке, корень изменится и мы это увидим
        for i, block in enumerate(self.chain):
            merkle_root = block.drevo_merkle()
            print(f"Блок {i} Merkle root: {merkle_root}") # выводим корни дерева Мёркла для каждого блока, если кто-то изменит транзакцию в блоке, корень изменится и мы это увидим
        return True

    def set_initial_state(self, balances): # задаём стартовые балансы аккаунтов
        self.state = copy.deepcopy(balances) # deepcopy чтобы не работать по ссылке и потом не удивляться почему всё поехало

    def execute_transaction(self, tx, temp_state): # функция исполняет ОДНУ транзакцию на временном состоянии
        # сначала базовые проверки, чтобы не было лютого бреда
        if tx.from_addr not in temp_state:
            return False, f"Отправитель {tx.from_addr} не существует"

        if tx.to_addr not in temp_state:
            return False, f"Получатель {tx.to_addr} не существует"

        if tx.amount <= 0:
            return False, f"Некорректная сумма {tx.amount}"

        tx_type = tx.payload.get("type", "transfer") # если тип не указан, считаем что это обычный перевод

        if tx_type == "transfer": # обычная транзакция без магии
            if temp_state[tx.from_addr] < tx.amount:
                return False, f"У {tx.from_addr} недостаточно средств"

            temp_state[tx.from_addr] -= tx.amount # снимаем деньги у отправителя
            temp_state[tx.to_addr] += tx.amount   # начисляем получателю
            return True, f"Обычный перевод {tx.amount} от {tx.from_addr} к {tx.to_addr}"

        elif tx_type == "contract_transfer": # это уже типа смарт контракт, тут есть условие
            min_balance = tx.payload.get("min_balance", 0) # минимальный баланс который должен быть у отправителя

            # условие контракта: переводить можно только если баланс отправителя > min_balance
            if temp_state[tx.from_addr] <= min_balance:
                return False, f"Контракт не выполнен: баланс {tx.from_addr} = {temp_state[tx.from_addr]}, нужно > {min_balance}"

            if temp_state[tx.from_addr] < tx.amount:
                return False, f"У {tx.from_addr} недостаточно средств для контракта"

            temp_state[tx.from_addr] -= tx.amount
            temp_state[tx.to_addr] += tx.amount
            return True, f"Контрактный перевод {tx.amount} от {tx.from_addr} к {tx.to_addr}, условие баланс > {min_balance} выполнено"

        else:
            return False, f"Неизвестный тип транзакции: {tx_type}" # если прилетело что-то непонятное, блок не должен пройти

    def add_block(self, transactions): # добавление нового блока в цепочку с выполнением транзакций
        temp_state = copy.deepcopy(self.state) # копируем текущее состояние, чтобы если что откатиться без боли и страданий
        local_logs = [] # временный лог именно для этого блока

        local_logs.append(f"Начата обработка нового блока с {len(transactions)} транзакциями")

        for i, tx in enumerate(transactions, start = 1): # по одной исполняем транзакции внутри блока
            ok, message = self.execute_transaction(tx, temp_state)
            local_logs.append(f"Транзакция {i}: {message}")

            if not ok: # если хотя бы одна транзакция кривая, весь блок летит в мусорку
                local_logs.append("ОШИБКА: блок отклонён, состояние откачено назад")
                self.logs.extend(local_logs)
                return False

        # если дошли сюда, значит все транзакции норм и можно реально создавать блок
        pred_block = self.chain[-1]
        new_block = Block(len(self.chain), time.time(), transactions, pred_block.hash)
        new_block.mine(self.difficulty)
        self.chain.append(new_block)

        self.state = temp_state # только теперь обновляем реальное состояние, а не раньше
        local_logs.append(f"Блок {new_block.index} успешно добавлен в цепочку")
        self.logs.extend(local_logs)
        return True

    def is_chain_valid(self): # проверка целостности цепочки, если кто-то изменит данные в блоке, хеш изменится и цепочка сломается
        target = "0" * self.difficulty

        for i in range(1, len(self.chain)): # проверяем каждый блок начиная со второго
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False # если содержимое блока не соответствует его хешу то кто-то мутил воду

            if current.previous_hash != previous.hash:
                return False # если ссылка на предыдущий блок неверная, цепочка сломана

            if not current.hash.startswith(target):
                return False # если блок не соответствует сложности майнинга то он невалидный

        if not self.chain[0].hash.startswith(target):
            return False # если генезис блок невалиден то всё очень плохо

        return True

    def print_chain(self): # вывод всех блоков в цепочке, для наглядности
        print("\nОТЧЁТ ПО БЛОКЧЕЙНУ:")
        print("=" * 60)

        for block in self.chain:
            print("_" * 60)
            print('index:', block.index)
            print('timestamp:', block.timestamp)
            print('previous_hash:', block.previous_hash)
            print('nonce:', block.nonce)
            print('hash:', block.hash)
            print('merkle_root:', block.drevo_merkle())
            print('transactions:')

            if len(block.transactions) == 0:
                print("  тут пусто потому что это нулевой блок, самый первый и священный")
            else:
                for tx in block.transactions:
                    print(" ", tx.to_dict())

    def print_state(self): # вывод текущего состояния аккаунтов
        print("\nТЕКУЩЕЕ СОСТОЯНИЕ БАЛАНСОВ:")
        print("=" * 60)
        for acc, balance in self.state.items():
            print(f"{acc}: {balance}")

    def print_logs(self): # вывод лога выполнения, чтобы видно было где всё получилось а где всё умерло
        print("\nЛ0Г ИСПОЛНЕНИЯ ТРАНЗАКЦИЙ:")
        print("=" * 60)
        for log in self.logs:
            print(log)


def demo(): # основная демонстрация лабораторки
    blockchain = Blockchain(4) # создаём блокчейн со сложностью 4, как у тебя в прошлой лр было

    # 3 аккаунта как просили в задании
    initial_balances = {
        "Alice": 100,
        "Bob": 60,
        "Charlie": 25
    }

    blockchain.set_initial_state(initial_balances)

    print("СТАРТОВЫЕ БАЛАНСЫ:")
    blockchain.print_state()

    # первый блок корректный, тут всё должно пройти
    block1_transactions = [
        Transaction("Alice", "Bob", 20, {"type": "transfer"}), # обычный перевод
        Transaction("Bob", "Charlie", 10, {"type": "transfer"}), # ещё один обычный перевод
        Transaction("Alice", "Charlie", 15, {"type": "contract_transfer", "min_balance": 50}) # контрактный перевод, пройдёт потому что у Alice больше 50
    ]

    print("\n" + "=" * 60)
    print("ДОБАВЛЯЕМ КОРРЕКТНЫЙ БЛОК")
    print("=" * 60)

    result1 = blockchain.add_block(block1_transactions)
    print("Результат добавления блока 1:", result1)
    blockchain.print_state()

    # второй блок некорректный, здесь должна сработать отмена всего блока
    block2_transactions = [
        Transaction("Charlie", "Bob", 5, {"type": "transfer"}), # эта транзакция сама по себе норм
        Transaction("Bob", "Alice", 20, {"type": "contract_transfer", "min_balance": 100}) # а вот эта уже не пройдёт, у бобика баланс не больше 100
    ]

    print("\n" + "=" * 60)
    print("ДОБАВЛЯЕМ НЕКОРРЕКТНЫЙ БЛОК")
    print("=" * 60)

    result2 = blockchain.add_block(block2_transactions)
    print("Результат добавления блока 2:", result2)

    # после неудачного блока состояние должно остаться как после первого блока
    print("\nСостояние после попытки добавить плохой блок:")
    blockchain.print_state()

    print("\nЦелостность цепочечки:", blockchain.is_chain_valid())
    print("Проверка дерева Мёркла:", blockchain.proverka_merkla())
    blockchain.print_logs()
    blockchain.print_chain()


if __name__ == "__main__":
    demo()