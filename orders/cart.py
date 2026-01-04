from decimal import Decimal
from catalog.models import Artwork

class Cart:
    SESSION_KEY = "cart" 

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(self.SESSION_KEY, {})

    def save(self):
        self.session[self.SESSION_KEY] = self.data
        self.session.modified = True

    def add(self, artwork_id, qty=1):
        pid = str(int(artwork_id))
        self.data[pid] = int(qty)
        self.save()

    def set(self, artwork_id, qty):
        pid = str(int(artwork_id))
        if int(qty) <= 0:
            self.data.pop(pid, None)
        else:
            self.data[pid] = int(qty)
        self.save()

    def remove(self, artwork_id):
        pid = str(int(artwork_id))
        if pid in self.data:
            del self.data[pid]
            self.save()

    def clear(self):
        self.session[self.SESSION_KEY] = {}
        self.session.modified = True

    def items(self):
        ids = [int(k) for k in self.data.keys()]
        for art in Artwork.objects.filter(id__in=ids, is_active=True).select_related("artist__user"):
            qty = self.data[str(art.id)]
            yield {
                "id": art.id,
                "title": art.title,
                "slug": art.slug,
                "price": art.price,
                "qty": qty,
                "subtotal": art.price * qty,
                "file_preview": getattr(art.file_preview, "url", None),
            }

    def __iter__(self):
        artworks = Artwork.objects.filter(id__in=self.data.keys())
        for art in artworks:
            yield {
                "art": art,
                "qty": self.data.get(str(art.id), 0),
            }

    def total(self):
        ids = list(self.data.keys())
        return sum(a.price for a in Artwork.objects.filter(id__in=ids))

    def count(self):
        return len(self.data)

    
    def get_total_price(self):
        artworks = Artwork.objects.filter(id__in=self.data.keys())
        return sum(art.price * self.data.get(str(art.id), 0) for art in artworks)
    

