import Anthropic from '@anthropic-ai/sdk';

const NOTION_VERSION = '2022-06-28';

/**
 * Notionのrich_textプロパティからプレーンテキストを抽出する
 */
function extractPlainText(property) {
  if (!property) return '';
  if (property.type === 'rich_text') {
    return property.rich_text.map((t) => t.plain_text).join('');
  }
  if (property.type === 'title') {
    return property.title.map((t) => t.plain_text).join('');
  }
  return '';
}

/**
 * Notionページの rich_text プロパティを更新する
 */
async function updateNotionRichText(pageId, propertyName, text) {
  const res = await fetch(`https://api.notion.com/v1/pages/${pageId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${process.env.NOTION_TOKEN}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      properties: {
        [propertyName]: {
          rich_text: [{ type: 'text', text: { content: text } }],
        },
      },
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(`Notion API エラー: ${err.message ?? res.status}`);
  }
  return res.json();
}

/**
 * Claude で要約する
 */
async function summarize(text) {
  const client = new Anthropic();
  const response = await client.messages.create({
    model: 'claude-opus-4-6',
    max_tokens: 1024,
    messages: [
      {
        role: 'user',
        content: `以下のテキストを簡潔に要約してください。要約文のみを返してください。\n\n${text}`,
      },
    ],
  });
  return response.content[0].text;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  try {
    const payload = req.body;

    // ★ デバッグ: Notionが送ってくるペイロードの全体を出力
    console.log('=== Notion webhook payload ===');
    console.log(JSON.stringify(payload, null, 2));

    // Notionオートメーションのペイロードは data 以下にページオブジェクトが入る場合と
    // 直接ページオブジェクトが来る場合がある
    const page = payload.data ?? payload;
    const pageId = page.id;
    const properties = page.properties;

    console.log('pageId:', pageId);
    console.log('properties keys:', properties ? Object.keys(properties) : 'none');

    if (!pageId || !properties) {
      return res.status(400).json({ error: 'Notionのペイロード形式が不正です', payload });
    }

    // ① 「要約前」プロパティの取得
    const sourceText = extractPlainText(properties['要約前']);
    console.log('要約前 text:', sourceText);

    if (!sourceText.trim()) {
      return res.status(400).json({ error: '「要約前」プロパティが空です' });
    }

    // ② Claude で要約
    const summary = await summarize(sourceText);

    // ③ 「要約後」プロパティに書き戻し
    await updateNotionRichText(pageId, '要約後', summary);

    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Notion webhook error:', error);
    return res.status(500).json({ error: error.message });
  }
}
