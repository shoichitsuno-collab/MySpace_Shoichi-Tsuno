/**
 * POST /api/crm
 * Slack スラッシュコマンド `/crm` を受け取り、トランスクリプト入力用 Modal を開く
 */

export const config = { maxDuration: 10 };

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { trigger_id, channel_id, user_id } = req.body;

  if (!trigger_id) {
    return res.status(400).json({ error: 'trigger_id is required' });
  }

  const slackToken = process.env.SLACK_BOT_TOKEN;
  if (!slackToken) {
    console.error('SLACK_BOT_TOKEN is not set');
    return res.status(500).json({ error: 'Slack token not configured' });
  }

  // Modal の定義
  const modal = {
    type: 'modal',
    callback_id: 'crm_transcript_modal',
    title: {
      type: 'plain_text',
      text: 'CRM登録 - 議事録作成',
    },
    submit: {
      type: 'plain_text',
      text: '送信して処理開始',
    },
    close: {
      type: 'plain_text',
      text: 'キャンセル',
    },
    // channel_id と user_id を private_metadata に保存（view_submission 時に参照）
    private_metadata: JSON.stringify({ channelId: channel_id, userId: user_id }),
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: '*tl;dv / Notta などからコピーしたトランスクリプトを貼り付けてください。*\n自動で企業・案件を特定し、Notion に議事録を登録します。',
        },
      },
      {
        type: 'divider',
      },
      {
        type: 'input',
        block_id: 'transcript_block',
        label: {
          type: 'plain_text',
          text: 'トランスクリプト',
        },
        element: {
          type: 'plain_text_input',
          action_id: 'transcript_input',
          multiline: true,
          placeholder: {
            type: 'plain_text',
            text: 'ここにトランスクリプトを貼り付けてください...',
          },
          min_length: 10,
        },
        hint: {
          type: 'plain_text',
          text: '文字数制限はありません。長文でもそのまま貼り付けてください。',
        },
      },
    ],
  };

  try {
    // Slack views.open API を呼び出して Modal を表示
    const response = await fetch('https://slack.com/api/views.open', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${slackToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trigger_id,
        view: modal,
      }),
    });

    const data = await response.json();

    if (!data.ok) {
      console.error('Slack views.open error:', data);
      // Slack にエラーメッセージを返す（ユーザーに見える）
      return res.status(200).json({
        response_type: 'ephemeral',
        text: `❌ Modal の表示に失敗しました: ${data.error}`,
      });
    }

    // Slack には空の 200 を返す（Modal が開く）
    return res.status(200).end();
  } catch (error) {
    console.error('Error opening modal:', error);
    return res.status(200).json({
      response_type: 'ephemeral',
      text: '❌ 内部エラーが発生しました。しばらく後に再試行してください。',
    });
  }
}
