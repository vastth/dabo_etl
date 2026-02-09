# -*- coding: utf-8 -*-
"""告警辅助模块：封装企业微信机器人发送逻辑，便于复用与替换。

对原实现做了小幅增强：
- 在 HTTP 200 后检查企业微信返回 JSON 的 `errcode` 是否为 0
- 超长消息截断为头+省略号+尾，保留上下文
- 更明确的异常捕获与日志记录
"""
import logging
from typing import List, Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def _truncate_message(content: str, max_len: int) -> str:
    if len(content) <= max_len:
        return content
    # 保留前后各一半内容，中间用省略号分隔
    half = max_len // 2 - 3
    if half <= 0:
        return content[-max_len:]
    head = content[:half]
    tail = content[-half:]
    return head + "\n...\n" + tail


def send_wechat_alert(
    webhook_url: str,
    content: str,
    mention_mobiles: Optional[List[str]] = None,
    max_len: int = 1500,
    timeout: int = 10,
) -> bool:
    """通过企业微信机器人 webhook 发送告警（text 类型）。

    返回 True 表示发送成功（HTTP 200 且企业微信返回 errcode==0），否则返回 False。

    参数:
    - `webhook_url`: 企业微信机器人的完整 webhook 地址
    - `content`: 要发送的文本内容
    - `mention_mobiles`: 可选的被 @ 的手机号列表
    - `max_len`: 单次发送的最大长度，超出时截断
    - `timeout`: 请求超时时间（秒）
    """
    if not webhook_url:
        logger.warning('No WECHAT_WEBHOOK configured, skip sending alert')
        return False

    text_to_send = _truncate_message(content, max_len)
    payload = {
        "msgtype": "text",
        "text": {"content": text_to_send},
    }
    if mention_mobiles:
        payload["text"]["mentioned_mobile_list"] = mention_mobiles

    try:
        logger.info("Wechat alert content:\n%s", text_to_send)
        resp = requests.post(webhook_url, json=payload, timeout=timeout)
    except RequestException:
        logger.exception('Network/Request exception when sending wechat alert')
        return False
    except Exception:
        logger.exception('Unexpected exception when sending wechat alert')
        return False

    # 尝试解析企业微信返回的 JSON 来判断是否成功
    if resp.status_code != 200:
        logger.error('Failed to send wechat alert, status=%s, body=%s', resp.status_code, resp.text)
        return False

    try:
        data = resp.json()
    except Exception:
        logger.warning('Wechat response is not JSON, treating send as failure: %s', resp.text)
        return False

    # 企业微信返回示例: {"errcode":0, "errmsg":"ok"}
    errcode = data.get('errcode')
    errmsg = data.get('errmsg')
    if errcode == 0:
        logger.info('Sent wechat alert successfully: %s', errmsg)
        return True
    else:
        logger.error('Wechat webhook returned error: errcode=%s, errmsg=%s, body=%s', errcode, errmsg, data)
        return False
