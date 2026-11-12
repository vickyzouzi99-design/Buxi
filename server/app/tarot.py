"""Code-owned 78-card draws. Names and prompts are original editorial data."""
import random
import secrets

MAJORS = [
("愚者","给一个新可能留出空间"),("魔术师","盘点你已经拥有的资源"),
("女祭司","留意尚未说出口的感受"),("皇后","照顾让你感到滋养的事"),
("皇帝","找到可以依靠的边界"),("教皇","检视你正在遵循的规则"),
("恋人","分清自己的价值与他人的期待"),("战车","选择一个能够推进的方向"),
("力量","尝试温柔而坚定地表达"),("隐者","给自己一些安静的时间"),
("命运之轮","区分可以改变和无法控制的部分"),("正义","把事实与猜测分开"),
("倒吊人","试着换一个观察位置"),("死神","思考什么阶段可以结束"),
("节制","给不同需要留出平衡"),("恶魔","留意让你失去自主的习惯"),
("高塔","重新检查已经不稳固的假设"),("星星","找一件让你恢复希望的小事"),
("月亮","承认不确定，不急着下结论"),("太阳","看见已经发生的进步"),
("审判","回看经历，更新对自己的理解"),("世界","认可完成，也允许新的开始")]
SUITS = [("wands","权杖","行动与热情"),("cups","圣杯","感受与关系"),
         ("swords","宝剑","思考与沟通"),("pentacles","星币","资源与日常")]
RANKS = ["一","二","三","四","五","六","七","八","九","十","侍从","骑士","王后","国王"]

DATA = __import__('json').loads((__import__('pathlib').Path(__file__).parent/'data/tarotoo.json').read_text())
SOURCES = __import__('json').loads((__import__('pathlib').Path(__file__).parent/'data/sources.json').read_text())
from .rules import SPREADS

def deck():
    names = [x[0] for x in MAJORS]
    cards=[]
    for source in DATA:
        rank=source['number_numerology']
        suit=source['suit']
        kind=next((x[1] for x in SUITS if x[0]==suit),'大阿尔卡那')
        cid=f"{suit}-{rank}" if suit else f"major-{source['id']}"
        cards.append(dict(id=cid,name=names[source['id']] if not suit else kind+RANKS[rank-1],
            kind=kind,arcana=source['arcana'],suit=suit,rank=rank,prompt=source['meaning_upright'],
            meanings={'upright':source['meaning_upright'],'reversed':source['meaning_reversed']},
            keywords={'upright':source['keywords_upright'],'reversed':source['keywords_reversed']},
            source={'name':'Tarotoo','url':'https://github.com/Tarotoo-com/tarotoo-tarot-dataset',
                    'revision':SOURCES['tarotoo'],'id':source['id']},
            contexts={k:source[k] for k in ['love','love_reversed','career','career_reversed']}))
    return cards

def draw(spread,rng=None,allow_reversed=True):
    rng=rng or secrets.SystemRandom()
    if spread not in SPREADS: raise ValueError('不支持的牌阵')
    remaining=deck()
    hand=[]
    # Independently implemented: random index -> remove card; same method as python-tarot.
    for position in SPREADS[spread]:
        card=remaining.pop(rng.randrange(len(remaining)))
        rev=rng.choice([True,False]) if allow_reversed else False
        hand.append(dict(card,position=position,reversed=rev,prompt=card['meanings']['reversed' if rev else 'upright']))
    return hand

def shuffled_deck(allow_reversed=True,rng=None):
    """Freeze a complete hidden deck before the user picks positions."""
    rng=rng or secrets.SystemRandom()
    cards=deck()
    rng.shuffle(cards)
    return [dict(c,reversed=rng.choice([True,False]) if allow_reversed else False) for c in cards]

def reflection(cards):
    return '\n\n'.join(f"{c['position']} · {c['name']}（{'逆位' if c['reversed'] else '正位'}）\n资料原文：{c['prompt']}" for c in cards)
