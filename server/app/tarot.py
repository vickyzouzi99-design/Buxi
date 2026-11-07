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

def deck():
    cards = [{"id":f"major-{i}","name":name,"kind":"大阿尔卡那","prompt":prompt}
             for i,(name,prompt) in enumerate(MAJORS)]
    for code,name,theme in SUITS:
        for i,rank in enumerate(RANKS):
            cards.append({"id":f"{code}-{i+1}","name":name+rank,"kind":name,
                          "prompt":f"从{theme}的角度，想想你此刻最需要关注的事"})
    return cards

def draw(spread, rng=None):
    rng = rng or secrets.SystemRandom()
    positions = {"single":["此刻的提醒"], "three":["当下","值得留意","可以尝试"]}
    if spread not in positions:
        raise ValueError("不支持的牌阵")
    return [dict(card, position=position, reversed=bool(rng.getrandbits(1)))
            for card,position in zip(rng.sample(deck(),len(positions[spread])),positions[spread])]

def reflection(cards):
    return "\n\n".join(
        f"{c['position']} · {c['name']}（{'逆位' if c['reversed'] else '正位'}）\n"
        + c["prompt"] + ("。逆位可作为反思阻碍或内在感受的角度，并不意味着坏事。" if c["reversed"]
                         else "。这是一个思考角度，不是对未来的断言。")
        for c in cards)
