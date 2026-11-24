from tunematch.pages.algorithms import *
from tunematch.pages.recommender import build_recommendations
from tunematch.pages.api_clients import APIError

# merge sort (stabil, asc/desc) & binary search
data=[{"t":"b","v":2},{"t":"a","v":2},{"t":"c","v":1}]
assert [x["t"] for x in merge_sort(data,key=lambda x:x["v"],reverse=True)]==["b","a","c"]
assert [x["t"] for x in merge_sort(data,key=lambda x:x["t"])]==["a","b","c"]
s=merge_sort([{"t":x} for x in ["hati","hari","dan","hujan"]],key=lambda x:x["t"])
assert [x["t"] for x in binary_search_prefix(s,"ha",key=lambda x:x["t"])]==["hari","hati"]
assert binary_search_prefix(s,"zz",key=lambda x:x["t"])==[]
# stack/queue
st=Stack(); st.push(1); st.push(2); assert st.pop()==2 and st.pop()==1 and st.pop() is None
q=Queue(); q.enqueue(1); q.enqueue(2); assert q.dequeue()==1 and len(q)==1
assert abs(jaccard(["a","b"],["b","c"])-1/3)<1e-9 and jaccard([],["a"])==0

class Fake:
    def top_tags(self,a,t,n=6): return ["chill","pop"] if t!="X" else (_ for _ in ()).throw(APIError("x"))
    def similar(self,a,t,l=30): return [{"title":"S1","artist":"A","match":0.9,"playcount":1000},
                                         {"title":"Dan","artist":"Fav","match":0.8,"playcount":5},
                                         {"title":"X","artist":"B","match":0.5,"playcount":10}]
    def tag_top_tracks(self,tag,l=20): return [{"title":"S1","artist":"A"},{"title":"T2","artist":"C"}]
r=build_recommendations(Fake(),[{"title":"Dan","artist":"Fav"}],["chill"],top_n=5)
assert all(x["title"]!="Dan" for x in r)            # favorit tidak ikut
assert len({x["key"] for x in r})==len(r)           # tanpa duplikat
assert r[0]["title"]=="S1" and r==sorted(r,key=lambda x:-x["score"])
print("tes inti lulus:",[(x["title"],round(x["score"],2)) for x in r])

# ekspor (jika dependensi tersedia)
try:
    from tunematch.pages.exporter import to_pdf_bytes,to_excel_bytes
    for x in r: x["explanation"]="Penjelasan ü uji"
    p=to_pdf_bytes(r,"santai",[{"title":"Dan","artist":"Fav"}],"ringkasan"); assert p[:4]==b"%PDF"
    e=to_excel_bytes(r,"santai",[{"title":"Dan","artist":"Fav"}],"ringkasan"); assert e[:2]==b"PK"
    print("ekspor PDF/Excel lulus",len(p),len(e))
except ImportError as ex: print("ekspor dilewati:",ex)
