"""Code for OpenAI API calls to generate story continuations and poll options."""

import json
import logging

from config import Config
from openai import OpenAI, OpenAIError


def generate_story_continuation(  # noqa: PLR0913
    openai_client: OpenAI,
    main_idea: str,
    current_story: str,
    user_choice: str,
    completion: float,
    config: Config,
    end_story: bool = False,
) -> tuple[str, str] | None:
    """Call OpenAI API to get the next story part using strict function calling."""
    truncated_story = current_story
    if len(current_story) > config.max_context_chars:
        logging.warning(
            f"Current story context ({len(current_story)} chars) "
            "exceeds limit ({max_context_chars}). Truncating.",
        )
        truncated_story = current_story[-config.max_context_chars :]
    # MAIN PROMPT
    system_prompt = """
Ты - самый великий современный творческий писатель, продолжающий интерактивную историю на русском языке.
Читатель контролирует историю и может влиять на ее направление, но ты имеешь основную нить сюжета и она соответствует традиционным канонам.
Тебе дан предыдущий текст истории и выбор пользователя (победитель опроса), который определяет следующее направление.

Твоя задача - написать СЛЕДУЮЩИЕ ТРИ ПАРАГРАФА истории, органично продолжая сюжет под влиянием выбора пользователя. Каждый параграф должен быть отделен пустой строкой.

###Правила напсиания###
- Никогда не обращайся к персонажу "герой" или "героиня", используй их имя и не меняй его, если это не необходимо для истории.

- Ты прекрасно знаешь как писать интересно и креативно. Твоя задча интерактивно менять историю, в зависимости от событий в рассказе - но вся история ДОЛЖНА БЫТЬ СВЯЗНОЙ и СЛЕДОВАТЬ ОСНОВНОЙ ИДЕЕ.

- Никогда не пиши с "AI SLOP"

- Меняй детальность истории, в зависимости от типов событий. Ниже — базовые «темпоральные правила» - «Тип события = сколько реального времени в среднем помещается в один абзац», а затем коротко — как выбор этих масштабов усиливает или снижает летальность сцены:

<temporal>
Фоновое описание обычного дня = ≈ 3 часа
Диалог (реплика ↔ ответ) = ≈ 5 минут
Битва / рукопашная схватка = ≈ 2 минуты
Кризис без боя (погоня, взлом, спасение) = ≈ 30 минут
Внутренний монолог / размышление = ≈ 45 минут
Переходное «прошла неделя» = ≈ 36 часов
Исторический дайджест, газетная вставка = ≈ 10 дней
</temporal>

- в случае если main_idea пуста, необходимо создать ее с нуля. это должно быть краткое описание всей будущей истории, с сюжетными ветками, развитием персонажей. История должна быть законченной и логичной, с четким началом, серединой и концом. Необходимо избегать клише и шаблонов, чтобы сделать историю уникальной и интересной.

- убедись, что main_idea содержит не только завязку и абстрактное описание истории, но и конкретные события (в том числе конец истории), которые произойдут в будущем. Это поможет создать более детализированную и увлекательную историю.

- меняй main_idea если выбор пользователя не совпадает с основным направлением сюжета, но избегай полной замены сюжета.


###Правила ответа###
- Возвращай результат ТОЛЬКО в формате JSON, используя предоставленный инструмент 'write_story_part' с полями:
- 'main_idea' - основная идея истории, которую ты должен учитывать при написании. она может слегка меняться от той что дана, но не должна быть изменена кардинально;
- 'reasoning' - твои мысли о том, как ты продолжишь историю чтобы действия пользователя органично вписались, добавь туда "две банальности которые ты избежишь" что избежать клише. Не параграфа на этот пункт;
- 'story_part' - сам текст следующих трех параграфов истории, не добавляй сюда мысли из reasoning, не ломай четвертую стену, не добавляй в этот раздел мысли про банальности;
Не добавляй никакого другого текста.

Всегда следуй ###Правила напсиания### и ###Правила ответа###.
"""  # noqa: E501

    user_prompt = f"""
Основная идея истории:
{main_idea}

Предыдущая история (завершена на {completion * 100}%):
{truncated_story}

Выбор пользователя: '{user_choice}'

Напиши следующие три параграфа, используя инструмент 'write_story_part'."""

    if end_story:
        system_prompt = f"""
Ты — самый великий современный творческий писатель, завершающий интерактивную историю на русском языке.
Тебе дан предыдущий текст истории.

Твоя задача — написать ЗАВЕРШАЮЩИЕ ТРИ ПАРАГРАФА истории, органично подводя итоги и развязывая все сюжетные ниточки под влиянием выбора пользователя. У тебя есть основная задумка сюжета и стоит ей следовать. Каждый параграф должен быть отделён пустой строкой и не превышать указанных «темпоральных» масштабов:

<temporal>
Фоновое описание финальных событий = ≈ 6 часов
Диалог, раскрывающий мотивацию и итоги = ≈ 10 минут
Внутренний монолог, осмысление пройденного пути = ≈ 1 час
Переход к эпилогу (“прошёл месяц/год…”) = ≈ 48 часов
</temporal>

### Правила написания ###
- Никогда не обращайся к персонажу “герой” или “героиня”, давай им имя.
- Всю историю нужно завершить связно, логично и эмоционально насыщенно: развяжи конфликты, ответь на ключевые вопросы, покажи, как изменились герои.
- Избегай шаблонных фраз и штампов: в разделе «reasoning» укажи две банальности, которых ты сознательно избежишь.
- Не ломай четвертую стену, не упоминай «AI SLOP».

### Правила ответа ###
- Верни результат ТОЛЬКО в формате JSON, используя инструмент `write_story_part` с полями:
  1. `reasoning` — твои мысли о том, как ты завершишь историю и какие две банальности ты избежишь;
  2. `story_part` — тексты трёх заключительных параграфов истории.

Не добавляй никакого другого текста.

Основная идея истории:
{main_idea}

Предыдущая история:
{truncated_story}
"""  # noqa: E501

    story_tool = {
        "type": "function",
        "function": {
            "name": "write_story_part",
            "description": "Записывает следующие три абзаца интерактивной истории и обоснование.",  # noqa: E501
            "strict": True,  # Enforce schema adherence
            "parameters": {
                "type": "object",
                "properties": {
                    "main_idea": {
                        "type": "string",
                        "description": "Основная идея истории, которую нужно учитывать при написании.",  # noqa: E501
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Краткое обоснование или план для следующих трех параграфов истории на русском языке.",  # noqa: E501
                    },
                    "story_part": {
                        "type": "string",
                        "description": "Текст следующих трех параграфов истории на русском языке, разделенных пустой строкой.",  # noqa: E501
                    },
                },
                "required": ["reasoning", "story_part"],
                "additionalProperties": False,
            },
        },
    }

    try:
        response = openai_client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[story_tool],
            tool_choice={
                "type": "function",
                "function": {"name": "write_story_part"},
            },
        )

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls and tool_calls[0].function.name == "write_story_part":
            try:
                arguments = json.loads(tool_calls[0].function.arguments)
            except json.JSONDecodeError as json_e:
                logging.error(
                    "Failed to parse JSON arguments "
                    f"from OpenAI story response: {json_e}",
                )
                logging.error(
                    f"Raw OpenAI arguments: {tool_calls[0].function.arguments}",
                )
                return None

            reasoning = arguments.get("reasoning", "[Обоснование не предоставлено]")
            story_part = arguments.get("story_part")
            main_idea = arguments.get("main_idea")
            logging.info(f"OpenAI Reasoning: {reasoning}")

            if story_part and story_part.strip() and main_idea and main_idea.strip():
                logging.info("OpenAI Story Part generated successfully.")
                # Add a newline for separation, ensure it's not just whitespace
                return ("\n\n" + story_part.strip(), main_idea.strip())
            logging.error(
                "OpenAI returned arguments but 'story_part' was empty or invalid.",
            )
            return None
        logging.error("Response did not contain the tool call 'write_story_part'.")
        logging.debug(f"OpenAI Full Response choice 0: {response.choices[0]}")
        return None

    except OpenAIError as e:
        logging.error(f"OpenAI API error during story generation: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error during story generation: {e}", exc_info=True)
        return None


def generate_poll_options(
    openai_client: OpenAI,
    full_story_context: str,
    config: Config,
    make_end_story_option: bool = False,
) -> list[str] | None:
    """Call OpenAI API to get 4 poll options using strict function calling."""
    story_options_count = 4
    logging.info("Generating poll options via OpenAI...")

    truncated_context = full_story_context[-config.max_context_chars :]

    system_prompt = """Ты - помощник для интерактивной истории на русском языке.
Тебе дан ПОЛНЫЙ текущий текст истории. Твоя задача - придумать ровно 4 КОРОТКИХ (максимум 90 символов!) и ФУНДАМЕНТАЛЬНО РАЗНЫХ варианта продолжения сюжета для опроса в Telegram.
Варианты должны быть МАКСИМАЛЬНО НЕПОХОЖИМИ друг на друга, предлагая совершенно разные, возможно, даже противоположные, направления развития событий (например, пойти на север ИЛИ пойти на юг ИЛИ остаться на месте ИЛИ искать что-то конкретное).
Избегай незначительных вариаций одного и того же действия. Нужны действительно ОТЛИЧАЮЩИЕСЯ выборы.
Возвращай результат ТОЛЬКО в формате JSON, используя предоставленный инструмент 'suggest_poll_options' с полем 'options' (массив из 4 строк). Не добавляй никакого другого текста."""  # noqa: E501

    user_prompt = f"""Полный текст текущей истории:
{truncated_context}

Предложи 4 варианта для опроса, используя инструмент 'suggest_poll_options'."""

    poll_tool = {
        "type": "function",
        "function": {
            "name": "suggest_poll_options",
            "description": "Предлагает 4 варианта продолжения для опроса в интерактивной истории.",  # noqa: E501
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "description": "List of exactly 4 concise story continuation options (max 90 chars each) in Russian.",  # noqa: E501
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "required": ["options"],
                "additionalProperties": False,
            },
        },
    }

    try:
        response = openai_client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[poll_tool],
            tool_choice={
                "type": "function",
                "function": {"name": "suggest_poll_options"},
            },
        )

        tool_calls = response.choices[0].message.tool_calls

        if tool_calls and tool_calls[0].function.name != "suggest_poll_options":
            logging.error(
                "Response did not contain the tool 'suggest_poll_options'."
                f"Full Response choice 0: {response.choices[0]}",
            )
            return None

        try:
            arguments = json.loads(tool_calls[0].function.arguments)
        except json.JSONDecodeError as e:
            logging.error(
                f"Failed to parse JSON arguments from OpenAI poll response: {e}."
                f"Raw OpenAI arguments: {tool_calls[0].function.arguments}",
            )
            return None

        options = arguments.get("options")
        if (
            isinstance(options, list)
            and len(options) == story_options_count
            and all(isinstance(opt, str) for opt in options)
        ):
            validated_options = [opt.strip()[:90] for opt in options if opt.strip()]
            if make_end_story_option:
                validated_options[3] = config.end_story_option
            if len(validated_options) == story_options_count:
                logging.info(f"OpenAI Poll Options generated: {validated_options}")
                return validated_options
            logging.error(f"OpenAI returned {len(validated_options)} valid options")
            logging.info(f"Original options from API: {options}")
            return None
        logging.error(
            "Returned invalid structure or content type for poll options."
            f"Received options: {options}",
        )
        return None
    except Exception as e:
        logging.error(f"Unexpected error during poll option generation: {e}")
        return None


def generate_imagen_prompt(
    openai_client: OpenAI,
    current_story: str,
    styling: str,
    openai_model: str,
) -> str | None:
    """
    Make a prompt for imagen.

    Generate a formatted prompt for image generation (e.g., Google Imagen) by
    combining a narrative story and styling instructions using OpenAI's function
    calling feature with strict function invocation.
    """
    tools = {
        "type": "function",
        "function": {
            "name": "format_image_prompt",
            "description": "Combines story and styling into a single image generation prompt.",  # noqa: E501
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The fully formatted and optimized image generation prompt.",  # noqa: E501
                    },
                },
                "required": ["prompt"],
            },
        },
    }

    # Prepare messages
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert prompt engineer. Transform the provided 'story' into a concise, vivid scene "  # noqa: E501
                "Always include descrition of the characters in the scene, mention their race (human, robot, elf, etc), their features."  # noqa: E501
                "description optimized for image generation (highlight key visual elements, mood, and composition). "  # noqa: E501
                "Also refine the raw 'styling' into a bullet-point list of clear style directives (e.g., art style, lighting, color palette, mood, composition). "  # noqa: E501
                "Return exactly one tool call to 'format_image_prompt' with a JSON object containing:\n"  # noqa: E501
                '{\n  "prompt": "..."\n}\n'
                "Where the 'prompt' string includes two formatted sections:\n"
                "[STYLING]\n- ...bullet points...\n\n"
                "[SCENE DESCRIPTION]\n...revised narrative...\n"
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"story": current_story, "styling": styling}),
        },
    ]
    logging.info(
        f"Generating an image prompt using styling: {styling[:100]} "
        f"and story: {current_story[:100]}...{current_story[-100:]}",
    )
    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=messages,
            tools=tools,
            tool_choice={
                "type": "function",
                "function": {"name": "format_image_prompt"},
            },
        )

        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "format_image_prompt":
            arguments = json.loads(tool_call.function.arguments)
            prompt = arguments.get("prompt")
            if prompt:
                return prompt
            logging.error("OpenAI did not return a valid prompt in the function call.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error during image prompt generation: {e}")
        return None
