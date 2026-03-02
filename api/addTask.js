export default async function handler(req, res) {
  // CORS設定
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  // OPTIONSリクエストに対応
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // POSTリクエストのみ受け付ける
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { taskText } = req.body;

    // 入力検証
    if (!taskText || taskText.trim() === '') {
      return res.status(400).json({ error: 'Task text is required' });
    }

    // 環境変数から取得
    const notionToken = process.env.NOTION_TOKEN;
    const databaseId = process.env.NOTION_DATABASE_ID;

    if (!notionToken || !databaseId) {
      return res.status(500).json({ error: 'Notion credentials not configured' });
    }

    // Notion API にリクエスト
    const response = await fetch('https://api.notion.com/v1/pages', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${notionToken}`,
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        parent: {
          database_id: databaseId.replace(/-/g, ''),
        },
        properties: {
          'タスク内容': {
            title: [
              {
                text: {
                  content: taskText,
                },
              },
            ],
          },
        },
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('Notion API error:', data);
      return res.status(response.status).json({
        error: data.message || 'Failed to create task in Notion',
        details: data,
      });
    }

    return res.status(200).json({
      success: true,
      message: 'Task added to Notion successfully',
      pageId: data.id,
    });
  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({
      error: 'Internal server error',
      message: error.message,
    });
  }
}
