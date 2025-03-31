import logging

import openai
from babeldoc.document_il.utils.atomic_integer import AtomicInteger
from pdf2zh.translator.base_translator import BaseTranslator
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

logger = logging.getLogger(__name__)


class OpenAITranslator(BaseTranslator):
    # https://github.com/openai/openai-python
    name = "openai"

    def __init__(
        self,
        lang_in,
        lang_out,
        model,
        base_url=None,
        api_key=None,
        ignore_cache=False,
    ):
        super().__init__(lang_in, lang_out, ignore_cache)
        self.options = {"temperature": 0}  # 随机采样可能会打断公式标记
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self.add_cache_impact_parameters("temperature", self.options["temperature"])
        self.model = model
        self.add_cache_impact_parameters("model", self.model)
        self.add_cache_impact_parameters("prompt", self.prompt(""))
        self.token_count = AtomicInteger()
        self.prompt_token_count = AtomicInteger()
        self.completion_token_count = AtomicInteger()

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(100),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        before_sleep=lambda retry_state: logger.warning(
            f"RateLimitError, retrying in {retry_state.next_action.sleep} seconds... "
            f"(Attempt {retry_state.attempt_number}/100)"
        ),
    )
    def do_translate(self, text) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            **self.options,
            messages=self.prompt(text),
        )
        self.token_count.inc(response.usage.total_tokens)
        self.prompt_token_count.inc(response.usage.prompt_tokens)
        self.completion_token_count.inc(response.usage.completion_tokens)
        return response.choices[0].message.content.strip()

    def prompt(self, text):
        return [
            {
                "role": "user",
                "content": f"You are a professional,authentic machine translation engine.\n\n;; Treat next line as plain text input and translate it into {self.lang_out}, output translation ONLY. If translation is unnecessary (e.g. proper nouns, codes, {'{{1}}, etc. '}), return the original text. NO explanations. NO notes. Input:\n\n{text}",
            },
        ]

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(100),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        before_sleep=lambda retry_state: logger.warning(
            f"RateLimitError, retrying in {retry_state.next_action.sleep} seconds... "
            f"(Attempt {retry_state.attempt_number}/100)"
        ),
    )
    def do_llm_translate(self, text):
        if text is None:
            return None

        response = self.client.chat.completions.create(
            model=self.model,
            **self.options,
            messages=[
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )
        self.token_count.inc(response.usage.total_tokens)
        self.prompt_token_count.inc(response.usage.prompt_tokens)
        self.completion_token_count.inc(response.usage.completion_tokens)
        return response.choices[0].message.content.strip()
