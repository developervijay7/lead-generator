import threading
import traceback

def test():
    try:
        from scraper_pw import scrape_google_maps

        def cb(c, t, m):
            print(f"  [{c}/{t}] {m}")

        results = scrape_google_maps(
    "restaurants in Agra, India",
    max_results=3,
    progress_callback=cb
)
        print(f"GOT {len(results)} results")
        for r in results:
            name = r.get("name", "?")
            phone = r.get("phone", "?")
            website = r.get("website", "None")
            print(f"  - {name} | {phone} | website={website}")
        print("THREAD SUCCESS")
    except Exception:
        traceback.print_exc()

t = threading.Thread(target=test)
t.start()
t.join(timeout=90)
print("DONE")
