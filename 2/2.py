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

def create_blockchainik(): # тута создаём цепочку из 5 блоков
    chain = [] # список где будут храниться ВСЕ блоки
    genesis = Block(0, time.time(), "Нулевой блок", "0")
    chain.append(genesis) # добавляем первый блок в список от греческого «γένεσις» = происхождение, рождение, возникновение как Книга Бытия в Библии

    for i in range(1,5): # создаём еще 4 блока чтобы было 5
        pred_block = chain[-1]
        new_block = Block(i, time.time(), f"Инфа для {i} блока", pred_block.hash)
        chain.append(new_block)
    return chain

def is_chain_valid(chain):
    for i in range (1, len(chain)):
        current = chain[i] #текущий блок
        previous = chain[i-1]
        if current.hash != current.calculate_hash():
            return False # если хеш изменился то цепочка сломана
        if current.previous_hash != previous.hash:
            return False # если ссылка неправильная то цепочка сломана
    return True

def print_chain(chain):
    for block in chain:
        print("_" * 60)
        print('index:', block.index)
        print('timestamp', block.timestamp)
        print('data:', block.data)
        print('previous_hash:', block.previous_hash)
        print('nonce', block.nonce)
        print('hash', block.hash)

if __name__ == "__main__":
    blockchain = create_blockchainik() # создание блокчейна
    print_chain(blockchain) # вывод всех блоков
    print('Целостность цепочечки?', is_chain_valid(blockchain)) # проверка целостности цепочки
