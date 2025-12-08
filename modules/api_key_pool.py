import random

class APIKeyPool:
    def __init__(self, keys, max_usage=20):
        self.max_usage = max_usage
        # dizionario: {api_key: numero_utilizzi}
        self.usage = {k: 0 for k in keys}

    def get_key(self):
        # filtra solo le chiavi ancora utilizzabili
        available = [k for k, u in self.usage.items() if u < self.max_usage]

        if not available:
            raise RuntimeError("Non ci sono più API key disponibili.")

        # scelta casuale
        key = random.choice(available)
        self.usage[key] += 1
        return key


# ESEMPIO D’USO
keys = [f"API_KEY_{i}" for i in range(1, 11)]
pool = APIKeyPool(keys)

print(pool.get_key())   # restituisce una key casuale tra le disponibili
