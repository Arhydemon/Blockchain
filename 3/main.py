import hashlib # SHA-256 хеш
import json    # данные блока в строку
import time    # просто время
from contracts import Transaction, do_all_transactions_one_block

class Block: # класс блок самый главный
    def __init__(self, index, timestamp, data, previous_hash, nonce = 0): # __init__ автоматический запуск при создании объекта
        self.index = index # селф указание что ИМЕННО ЭТОТ БЛОК
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce # кто не шарит тот не шарит
        self.hash = self.calculate_hash() # hash это цифровой отпечаток блока типа отпечаток как на пальцах

    def calculate_hash(self): # все поля блока собираем в один
        # ВАЖНО: теперь data может быть списком транзакций,
        # json.dumps не умеет хешировать объекты -> превращаем их в словари
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
        # SHA-256 понимает только байты, .encode() превращает строку в байты
        # json.dumps превращает словаоб в строку
        # sort_keys заставляет ключи идти в одном и том же порядке всегда
        # hashlib.sha256(block_string) создание SHA-256 объекта хеширования, он берёт байты и вычисляет их цифровой отпечаток.
        block_string = json.dumps(block_data, sort_keys = True, ensure_ascii=False).encode()
        return hashlib.sha256(block_string).hexdigest() # .hexdigest превращает его в удобную строку из букв и цифр:

    def mine(self, difficulty): 
        target="0" * difficulty
        self.nonce = 0

        while True:
            self.hash = self.calculate_hash()
            if self.hash[:difficulty] == target:
                break
            else:
                self.nonce += 1 

# блокчейн который хранит balances (state) и добавляет блоки с транзакциями
class Blockchainik:
    def __init__(self, difficulty, genesis_state):
        self.difficulty = difficulty
        self.state = dict(genesis_state) # тут балансы
        self.chain = [] # тут блоки
        self.logs = []  # лог выполнения транзакций

        # genesis block (нулевой)
        genesis = Block(0, time.time(), [], "0")
        genesis.mine(difficulty)
        self.chain.append(genesis)
        self.logs.append("GENESIS: state=" + str(self.state))

    def add_block(self, tx_list):
        pred_block = self.chain[-1]
        new_block = Block(len(self.chain), time.time(), tx_list, pred_block.hash)
        new_block.mine(self.difficulty)

        # ВАЖНООО АЛО ОЧЕНЬ ВАЖНОО: выполняем транзакции и если ошибка -> откат, блок не добавляем
        result = do_all_transactions_one_block(self.state, tx_list)
        log = result[1]
        ok = result[2]
        self.logs.append("\n" + "_" * 60)
        self.logs.append(f"BLOCK #{new_block.index} mined hash={new_block.hash[:10]}...")
        self.logs.extend(log)

        if ok:
            self.chain.append(new_block)
            self.logs.append("BLOCK ADDED, state=" + str(self.state))
        else:
            self.logs.append("BLOCK REJECTED (ROLLBACK), state=" + str(self.state))

        return ok


def is_chain_valid(chain, difficulty): # проверка целостности цепочки, если кто-то изменит данные в блоке, то хеш изменится и цепочка будет сломана
    target = "0" * difficulty # проверка каждого блока начиная со второго, так как нулевой блок не на что не ссылается
    for i in range (1, len(chain)):
        current = chain[i] #текущий блок
        previous = chain[i-1]
        if current.hash != current.calculate_hash():
            return False # если хеш изменился то цепочка сломана
        if current.previous_hash != previous.hash:
            return False # если ссылка неправильная то цепочка сломана
        if not current.hash.startswith(target):
            return False # если блок не майнится то цепочка сломана
    if not chain[0].hash.startswith(target):
        return False # если нулевой блок не майнится то цепочка сломана
    return True


def print_chain(chain): # вывод всех блоков в цепочке, для наглядности
    for block in chain:
        print("_" * 60)
        print('index:', block.index)
        print('timestamp', block.timestamp)

        # data теперь может быть список транзакций
        if type(block.data) is list:
            print('data (transactions):')
            for tx in block.data:
                print("   ", tx.frm, "->", tx.to, "amount=", tx.amount, "payload=", tx.payload)
        else:
            print('data:', block.data)

        print('previous_hash:', block.previous_hash)
        print('nonce', block.nonce)
        print('hash', block.hash)


# report оставим, но он теперь не очень подходит под транзакции
# чтобы твой код не ломать — оставим, просто будет майнить генезис + пустые блоки (по сути)
def report():
    print("ОТЧЁТ ПО БЛОКЧЕЙНУ:")
    print("=" * 40)

    for difficulty in [1,2,3,4,5]: # проверяем разные сложности майнинга
        start = time.perf_counter() # замер времени, perf_counter() возвращает время в секундах с высокой точностью, идеально для измерения времени выполнения кода

        # создаём маленькую цепочку без транзакций чисто для замера pow
        bc = Blockchainik(difficulty, {"A": 100})
        # добавим 4 пустых блока, чтобы было 5 как раньше
        for _ in range(4):
            bc.add_block([])

        end = time.perf_counter() # замер времени окончания
        total_time = end - start
        avg_time = total_time / len(bc.chain)

        print(f"Сложность: {difficulty}, Время: {total_time:.2f} секунд, Среднее время: {avg_time:.2f} секунд, Проверка PoW: {is_chain_valid(bc.chain, difficulty)}")        


if __name__ == "__main__":
    difficulty = 4 # сложность майнинга, чем выше тем дольше майнится блок

    # СЦЕНАРИЙ ИЗ ЗАДАНИЯ:
    # 3 аккаунта, серия транзакций, один контракт с условием,
    # потом некорректный блок и откат

    bc = Blockchainik(difficulty, {
        "Alice": 100,
        "Bob": 40,
        "Charlie": 10
    })

    # блок 1: корректные обычные переводы
    block1 = [
        Transaction("Alice", "Bob", 25),
        Transaction("Bob", "Charlie", 10),
    ]
    bc.add_block(block1)

    # блок 2: контракт (перевод только если баланс отправителя > X)
    block2 = [
        Transaction("Alice", "Charlie", 20, {"type": "cond", "min_balance": 50}),
    ]
    bc.add_block(block2)

    # блок 3: некорректный (должен откатиться ВЕСЬ блок)
    block3 = [
        Transaction("Charlie", "Alice", 5),
        Transaction("Bob", "Alice", 30, {"type": "cond", "min_balance": 100}), # заведомо не выполнится
    ]
    bc.add_block(block3)

    # вывод логов исполнения транзакций (по заданию надо логи)
    print("\n" + "=" * 60)
    print("ЛОГИ ИСПОЛНЕНИЯ:")
    print("=" * 60)
    for line in bc.logs:
        print(line)

    # вывод блоков
    print("\n" + "=" * 60)
    print("ЦЕПОЧКА:")
    print("=" * 60)
    print_chain(bc.chain)

    # проверка целостности цепочки
    print("\nЦелостность цепочечки:", is_chain_valid(bc.chain, difficulty))
    report()