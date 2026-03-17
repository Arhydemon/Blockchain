import hashlib # SHA-256 хеш
import json    # данные блока в строку
import time    # просто время

class Block: # класс блок самый главный
    def __init__(self, index, timestamp, data, previous_hash, nonce = 0): # __init__ автоматический запуск при создании объекта
        self.index = index # селф указание что ИМЕННО ЭТОТ БЛОК
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce # кто не шарит тот не шарит
        self.hash = self.calculate_hash() # hash это цифровой отпечаток блока типа отпечаток как на пальцах

    def calculate_hash(self): # все поля блока собираем в один
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        # SHA-256 понимает только байты, .encode() превращает строку в байты
        # json.dumps превращает словаоб в строку
        # sort_keys заставляет ключи идти в одном и том же порядке всегда
        # hashlib.sha256(block_string) создание SHA-256 объекта хеширования, он берёт байты и вычисляет их цифровой отпечаток.
        block_string = json.dumps(block_data, sort_keys = True).encode()
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

def create_blockchainik(difficulty): # тута создаём цепочку из 5 блоков
    chain = [] # список где будут храниться ВСЕ блоки
    genesis = Block(0, time.time(), "Нулевой блок", "0")
    genesis.mine(difficulty) # майним нулевой блок, чтобы он был валидным, иначе вся цепочка будет сломана
    chain.append(genesis) # добавляем первый блок в список от греческого «γένεσις» = происхождение, рождение, возникновение как Книга Бытия в Библии

    for i in range(1,5): # создаём еще 4 блока чтобы было 5
        pred_block = chain[-1]
        new_block = Block(i, time.time(), f"Инфа для {i} блока", pred_block.hash)
        new_block.mine(difficulty)
        chain.append(new_block)
    return chain

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
        print('data:', block.data)
        print('previous_hash:', block.previous_hash)
        print('nonce', block.nonce)
        print('hash', block.hash)

def report():
    print("ОТЧЁТ ПО БЛОКЧЕЙНУ:")
    print("=" * 40)

    for difficulty in [1,2,3,4,5]: # проверяем разные сложности майнинга
        start = time.perf_counter() # замер времени, perf_counter() возвращает время в секундах с высокой точностью, идеально для измерения времени выполнения кода
        chain = create_blockchainik(difficulty)
        end = time.perf_counter() # замер времени окончания
        total_time = end - start
        avg_time = total_time / len(chain)

        print(f"Сложность: {difficulty}, Время: {total_time:.2f} секунд, Среднее время: {avg_time:.2f} секунд, Проверка PoW: {is_chain_valid(chain, difficulty)}")        

if __name__ == "__main__":
    difficulty = 4 # сложность майнинга, чем выше тем дольше майнится блок
    blockchain = create_blockchainik(difficulty) # создание блокчейна
    print_chain(blockchain) # вывод всех блоков
    if is_chain_valid(blockchain, difficulty): # проверка целостности цепочки
        print('Целостность цепочечки:', is_chain_valid(blockchain, difficulty))
    report()

    