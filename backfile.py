#!/usr/bin/python3
import sys
import requests
import random
import time
import threading
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# Couleurs ANSI
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
FAIL = '\033[91m'
RESET = '\033[0m'

# User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Headers additionnels
COMMON_HEADERS = [
    {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"},
    {"Accept-Language": "en-US,en;q=0.5"},
    {"Accept-Encoding": "gzip, deflate"},
    {"DNT": "1"},
    {"Connection": "keep-alive"},
    {"Upgrade-Insecure-Requests": "1"},
]

# Extensions et fichiers à tester
EXTENSIONS = [
    ".bak", ".backup", ".bck", ".save", ".sav", ".copy", ".old", ".orig", ".tmp", ".temp",
    ".back", ".bkp", ".bac", ".swp", ".swo", ".swn", ".~", ".1", ".2", ".inc", ".tar",
    ".gz", ".tar.gz", ".zip", ".rar", ".7z", ".bz2", ".tgz", ".z", ".sql", ".sqlite",
    ".db", ".dbf", ".mdb", ".bak.sql", ".sql.gz", ".sql.bak", ".php", ".php~", ".php.bak",
    ".php.old", ".php.inc", ".php.swp", ".html", ".html~", ".html.bak", ".htm", ".asp",
    ".aspx", ".jsp", ".txt", ".log", ".conf", ".cfg", ".config", ".ini", ".env", ".env.bak",
    ".env.save", ".xml", ".xml.bak", ".json", ".json.bak", ".yaml", ".yml", ".properties",
    ".sh", ".bash", ".sql~", ".dump", ".data", ".dat", ".bak2", ".bak3", ".DS_Store",
    ".db_store", ".git", ".svn", ".htaccess", ".htpasswd", ".gitignore", ".lock", ".md",
    ".markdown", ".rst", ".bakup", ".archive", ".tar.bz2", ".zipx", ".pem", ".key", ".crt",
    ".cer", ".csr", ".pfx", ".pub", ".ssh", ".id_rsa", ".doc", ".docx", ".xls", ".xlsx",
    ".pdf", ".ppt", ".pptx", ".rtf", ".BAK", ".BACKUP", ".BCK", ".SAVE", ".SAV", ".COPY",
    ".OLD", ".ORIG", ".TMP"
]
AUTO_FILES = ["install", "login", "admin", "wp-config", "test", "backup", "back", "admin.inc",
              "inc", "administrateur", "administrator", "config", "conf", "cnf", "configuration",
              "index", "setup", ""]
SUFFIXES = ["", ".html", ".php"]

def get_random_headers():
    """Génère des headers aléatoires pour éviter la détection."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(["en-US,en;q=0.5", "fr-FR,fr;q=0.9", "de-DE,de;q=0.8"]),
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Ajouter parfois des headers supplémentaires
    if random.choice([True, False]):
        headers["Cache-Control"] = random.choice(["no-cache", "max-age=0"])
    
    if random.choice([True, False, False]):  # 33% chance
        headers["Referer"] = "https://www.google.com/"
    
    return headers

def make_request(url, delay_range=(0.5, 2.0), retries=2, session=None):
    """Fait une requête avec gestion des erreurs et délai aléatoire."""
    for attempt in range(retries + 1):
        try:
            # Délai aléatoire entre les requêtes
            time.sleep(random.uniform(*delay_range))
            
            headers = get_random_headers()
            
            # Utiliser une session si fournie (pour les cookies)
            requester = session if session else requests
            response = requester.get(url, headers=headers, timeout=10, allow_redirects=False)
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise e
            # Délai plus long en cas d'erreur avant retry
            time.sleep(random.uniform(2.0, 4.0))
    
    return None

def scan_files(url, filename=None, show_false_positives=False, verbose=False, threads=5, delay_range=(0.5, 2.0)):
    """Scanne les fichiers sur le serveur avec les extensions données."""
    if not url.endswith("/"):
        url += "/"

    files_to_test = AUTO_FILES if filename is None else [filename]
    
    # Créer une session pour maintenir les cookies
    session = requests.Session()
    
    # Obtenir la taille de la page de base pour détecter les faux-positifs
    print(f"{OKBLUE}Getting baseline response size...{RESET}")
    try:
        baseline_response = make_request(url, delay_range=(0, 0), session=session)  # Pas de délai pour la baseline
        if baseline_response is None:
            print(f"{FAIL}Failed to get baseline response{RESET}")
            return 0
            
        baseline_size = len(baseline_response.content)
        baseline_status = baseline_response.status_code
        print(f"{OKBLUE}Baseline: {url} - Status: {baseline_status} - Size: {baseline_size} bytes{RESET}")
        
        # Détecter les pages d'erreur communes
        baseline_content = baseline_response.text.lower()
        error_indicators = ['404', 'not found', 'error', 'forbidden', 'access denied']
        is_error_page = any(indicator in baseline_content for indicator in error_indicators)
        
        if is_error_page and verbose:
            print(f"{FAIL}Warning: Baseline appears to be an error page{RESET}")
            
    except requests.exceptions.RequestException as e:
        print(f"{FAIL}Error getting baseline: {e}{RESET}")
        return 0

    # Calcul du nombre total de requêtes
    total_requests = len(files_to_test) * len(EXTENSIONS) * len(SUFFIXES)
    current_request = 0
    found = 0
    false_positives = 0
    lock = threading.Lock()

    print(f"{'='*60}")
    print(f"{OKBLUE}Scanning {url} [{'Auto' if filename is None else filename}] with {threads} threads{RESET}")
    print(f"{OKBLUE}Total requests: {total_requests} | Delay: {delay_range[0]}-{delay_range[1]}s{RESET}\n")

    def test_url(file, ext, suffix):
        nonlocal current_request, found, false_positives
        
        test_url = f"{url}{file}{suffix}{ext}"
        try:
            r = make_request(test_url, delay_range, session=session)
            if r is None:
                return
                
            if r.status_code == 200:
                response_size = len(r.content)
                
                # Tolérance de 5% pour les petites variations (timestamps, etc.)
                size_tolerance = baseline_size * 0.05
                size_diff = abs(response_size - baseline_size)
                
                # Vérifier si c'est un vrai fichier backup ou juste la page de base
                if size_diff > size_tolerance:
                    with lock:
                        found += 1
                        print(f"\n{OKGREEN} ✓ BACKUP FOUND: {OKBLUE}{test_url}{RESET}")
                        print(f"   Size: {response_size} bytes (baseline: {baseline_size} bytes, diff: {size_diff})")
                else:
                    with lock:
                        false_positives += 1
                        if verbose:
                            print(f"\n{FAIL} ✗ False positive (similar size to baseline): {test_url}{RESET}")
                            print(f"   Size: {response_size} bytes (baseline: {baseline_size} bytes, diff: {size_diff})")
            elif r.status_code == 403 and verbose:
                with lock:
                    print(f"\n{FAIL} ⚠ Forbidden (potential backup): {test_url}{RESET}")
                        
        except (requests.exceptions.RequestException, KeyboardInterrupt) as e:
            if verbose:
                with lock:
                    print(f"\n{FAIL}Error testing {test_url}: {e}{RESET}")

        # Mise à jour du pourcentage de progression
        with lock:
            current_request += 1
            progress = (current_request / total_requests) * 100
            bar_length = 30
            filled = int(bar_length * progress // 100)
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f"\rProgress: |{bar}| {progress:>5.1f}%", end="", flush=True)

    # Préparer toutes les URLs à tester
    test_params = []
    for file in files_to_test:
        for ext in EXTENSIONS:
            for suffix in SUFFIXES:
                test_params.append((file, ext, suffix))

    # Mélanger l'ordre pour éviter les patterns détectables
    random.shuffle(test_params)

    # Exécution multi-threadée
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(test_url, file, ext, suffix) for file, ext, suffix in test_params]
        
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print(f"\n{FAIL}Scan interrupted by user{RESET}")
            return found

    print(f"\n\n{'='*60}")
    print(f"{OKGREEN}Legitimate Backup Files Found: {found}{RESET}")
    print(f"{FAIL}False Positives Filtered: {false_positives}{RESET}")
    print(f"{'='*60}")
    return found

def help_menu():
    """Affiche le menu d'aide."""
    print(f"Usage:\n")
    print("  backfile.py [URL] [FILE] [OPTIONS]")
    print("  Ex: backfile.py http://example.com index\n")
    print("  backfile.py [URL] --auto [OPTIONS]")
    print("  Ex: backfile.py http://example.com --auto\n")
    print("Options:")
    print("  --verbose              Show false positives and debugging information")
    print("  --threads N            Number of concurrent threads (default: 5)")
    print("  --delay MIN-MAX        Delay range between requests in seconds (default: 0.5-2.0)")
    print("  --stealth              Use longer delays and fewer threads for stealth")
    print("  --fast                 Use shorter delays and more threads for speed")
    print("  --show-false-positives (deprecated, use --verbose instead)\n")
    print("Auto mode tests: login, admin, wp-config, test, backup, etc.\n")
    print("WAF Evasion Features:")
    print("  • Random User-Agent rotation")
    print("  • Random header generation")
    print("  • Request order randomization") 
    print("  • Configurable delays between requests")
    print("  • Multi-threaded scanning")
    print("  • Error detection and retry logic\n")
    print("Note: The script automatically filters false positives by comparing")
    print("response sizes with the baseline page. Use --verbose to see filtered results.\n")

def main():
    """Point d'entrée principal."""
    try:
        if len(sys.argv) < 2:
            help_menu()
            return
            
        url = sys.argv[1]
        
        # Parse des arguments
        show_false_positives = "--show-false-positives" in sys.argv
        verbose = "--verbose" in sys.argv
        
        # Paramètres de performance
        threads = 5
        delay_range = (0.5, 2.0)
        
        # Parse des options avancées
        for i, arg in enumerate(sys.argv):
            if arg == "--threads" and i + 1 < len(sys.argv):
                try:
                    threads = int(sys.argv[i + 1])
                    threads = max(1, min(20, threads))  # Limite entre 1 et 20
                except ValueError:
                    print(f"{FAIL}Invalid thread count. Using default: 5{RESET}")
                    
            elif arg == "--delay" and i + 1 < len(sys.argv):
                try:
                    delay_parts = sys.argv[i + 1].split('-')
                    if len(delay_parts) == 2:
                        min_delay = float(delay_parts[0])
                        max_delay = float(delay_parts[1])
                        if min_delay >= 0 and max_delay > min_delay:
                            delay_range = (min_delay, max_delay)
                except ValueError:
                    print(f"{FAIL}Invalid delay format. Use: --delay 0.5-2.0{RESET}")
                    
        # Modes prédéfinis
        if "--stealth" in sys.argv:
            threads = 2
            delay_range = (2.0, 5.0)
            print(f"{OKBLUE}Stealth mode: {threads} threads, {delay_range[0]}-{delay_range[1]}s delay{RESET}")
            
        elif "--fast" in sys.argv:
            threads = 10
            delay_range = (0.1, 0.5)
            print(f"{OKBLUE}Fast mode: {threads} threads, {delay_range[0]}-{delay_range[1]}s delay{RESET}")
        
        # Filtrer les options des arguments
        args = [arg for arg in sys.argv[2:] if not arg.startswith("--") and not any(
            sys.argv[max(0, i-1)] in ["--threads", "--delay"] for i, a in enumerate(sys.argv) if a == arg
        )]
        mode = args[0] if args else None

        if mode == "auto":
            scan_files(url, show_false_positives=show_false_positives, verbose=verbose, threads=threads, delay_range=delay_range)
        elif mode:
            scan_files(url, mode, show_false_positives=show_false_positives, verbose=verbose, threads=threads, delay_range=delay_range)
        else:
            help_menu()
    except IndexError:
        help_menu()
    except KeyboardInterrupt:
        print(f"\n{FAIL}Scan interrupted by user{RESET}")

if __name__ == "__main__":
    main()
