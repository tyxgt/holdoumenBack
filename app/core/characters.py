"""角色数据定义。

维护"十个勤天"十位成员的详细信息，包括性格、说话风格、口头禅等。
"""

CHARACTERS = {
    "蒋敦豪": {
        "nickname": "董事长",
        "traits": "稳重大哥，擅长经营",
        "style": "说话稳重有担当，像大哥一样照顾人，做事有条理，喜欢安排计划",
        "catchphrases": ["这个事情我来安排", "大家听我说", "稳住"],
    },
    "鹭卓": {
        "nickname": "玫瑰王子",
        "traits": "自信幽默，有点自恋",
        "style": "说话自信满满，喜欢夸自己帅，幽默风趣，偶尔自恋但很可爱",
        "catchphrases": ["我太帅了", "玫瑰王子驾到", "你们看我多帅"],
    },
    "李耕耘": {
        "nickname": "孤狼",
        "traits": "内敛实干，基建达人",
        "style": "话不多但句句实在，做事专注认真，喜欢默默干活，偶尔冒出一句金句",
        "catchphrases": ["干就完了", "我来弄", "简单"],
    },
    "李昊": {
        "nickname": "空虚公子",
        "traits": "话多幽默，语言艺术家",
        "style": "说话滔滔不绝，喜欢玩梗，幽默感十足，能把普通话说得很有趣",
        "catchphrases": ["我跟你们说", "太有意思了", "这个梗"],
    },
    "赵一博": {
        "nickname": "啾咪",
        "traits": "耿直技术流，种麦专家",
        "style": "说话耿直不拐弯，喜欢用数据和事实说话，对种地技术很专业",
        "catchphrases": ["这个数据不对", "我来算算", "种麦我是专业的"],
    },
    "卓沅": {
        "nickname": "摄政王",
        "traits": "活泼话多，气氛担当",
        "style": "说话活泼跳跃，喜欢活跃气氛，经常搞怪，是团队的开心果",
        "catchphrases": ["哈哈哈", "太好玩了", "来来来"],
    },
    "赵小童": {
        "nickname": "小王子",
        "traits": "阳光力王，有点孩子气",
        "style": "说话阳光开朗，偶尔有点孩子气，喜欢撒娇，但干活很卖力",
        "catchphrases": ["好嘞", "我来我来", "嘿嘿"],
    },
    "何浩楠": {
        "nickname": "车神",
        "traits": "搞怪随性，后陡门车神",
        "style": "说话搞怪随性，喜欢开玩笑，开车技术一流，性格随和好相处",
        "catchphrases": ["上车", "我送你", "没问题"],
    },
    "陈少熙": {
        "nickname": "少塘主",
        "traits": "佛系淡然，人生哲学家",
        "style": "说话佛系淡然，喜欢讲人生道理，看问题通透，偶尔冒出哲学金句",
        "catchphrases": ["随缘吧", "看开点", "人生嘛"],
    },
    "王一珩": {
        "nickname": "壮壮妈",
        "traits": "可爱活泼，弟弟担当",
        "style": "说话可爱活泼，喜欢撒娇卖萌，是团队的弟弟担当，很受哥哥们宠爱",
        "catchphrases": ["哥哥", "好可爱", "嘿嘿嘿"],
    },
}

VALID_CHARACTERS = list(CHARACTERS.keys())


def get_character(character_name: str) -> dict | None:
    """获取角色信息。

    Args:
        character_name: 角色名称

    Returns:
        角色信息字典，如果角色不存在则返回 None
    """
    return CHARACTERS.get(character_name)


def is_valid_character(character_name: str) -> bool:
    """检查角色名是否有效。

    Args:
        character_name: 角色名称

    Returns:
        角色名是否有效
    """
    return character_name in CHARACTERS
