"""模块等级修正逻辑。"""


def adjust_module_level(initial_level: int, correct_count: int) -> int:
    """
    根据自评等级与校验答对题数修正最终模块等级。
    - 初始1：保持1
    - 初始2：全错→1，至少对1道→2
    - 初始3：全错→2，至少对1道→3
    - 初始4：对≤1道→3，对2道→4
    """
    initial = max(1, min(4, int(initial_level)))
    correct = max(0, int(correct_count))

    if initial == 1:
        return 1
    if initial == 2:
        return 2 if correct >= 1 else 1
    if initial == 3:
        return 3 if correct >= 1 else 2
    # initial == 4
    return 4 if correct >= 2 else 3
