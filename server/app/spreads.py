"""Project spreads, independently versioned from card knowledge."""
SPREADS = {'single':['此刻的提醒'], 'three':['当下','值得留意','可以尝试'], 'reflection':['现状','阻碍','建议']}
SPREAD_VERSION = 'buxi-spreads-2026-11-11.1'
SPREAD_DEFINITIONS = {
 'single':[{'id':'reminder','name':'此刻的提醒','meaning':'一个值得观察的主题，不保证全天运势'}],
 'three':[{'id':'present','name':'当下','meaning':'当下主题'}, {'id':'attention','name':'值得留意','meaning':'需要核实的细节'}, {'id':'action','name':'可以尝试','meaning':'一个可选的小行动'}],
 'reflection':[{'id':'situation','name':'现状','meaning':'描述当下处境'}, {'id':'obstacle','name':'阻碍','meaning':'探索相关品质是否过量或不合时宜，不改变正逆牌义'}, {'id':'advice','name':'建议','meaning':'提出可选行动，不替用户决定'}]
}
