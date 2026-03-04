/**
 * POST /api/crm-action
 * Slack Interactive Components のエンドポイント
 * - view_submission: Modal 送信後の処理（トランスクリプト受信 → 企業検索）
 * - block_actions: ボタンクリック処理（企業選択 / 案件選択 / 議事録確認）
 */

import Anthropic from '@anthropic-ai/sdk';
import { kv } from '@vercel/kv';
import { randomUUID } from 'crypto';
import { waitUntil } from '@vercel/functions';

export const config = { maxDuration: 60 };

// ─────────────────────────────────────────────────────────────
// Notion DB ID 定数（crm.md より）
// ─────────────────────────────────────────────────────────────
const COMPANY_DB_ID  = '2065fb52-a4aa-810b-ae88-d9c780f1b177'; // 企業DB
const CASE_DB_ID     = '2065fb52-a4aa-8105-983a-ecb644a8b678'; // 案件DB
const DOCUMENT_DB_ID = '2065fb52-a4aa-81f9-834a-c46b39b18fcd'; // ドキュメントDB

const NOTION_VERSION = '2022-06-28';

// ─────────────────────────────────────────────────────────────
// Notion API ヘルパー
// ─────────────────────────────────────────────────────────────

/** Notion DB をテキストで検索（企業DB: titleフィールド "企業名" でフィルタ） */
async function queryCompanyDB(searchText) {
  const res = await fetch(`https://api.notion.com/v1/databases/${COMPANY_DB_ID}/query`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.NOTION_TOKEN}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filter: {
        property: '企業名',
        title: { contains: searchText },
      },
      page_size: 5,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Notion 企業DB query error: ${data.message}`);
  return data.results ?? [];
}

/** 案件DB を企業ページID（relation）でフィルタして検索 */
async function queryCaseDB(companyPageId) {
  const res = await fetch(`https://api.notion.com/v1/databases/${CASE_DB_ID}/query`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.NOTION_TOKEN}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filter: {
        property: '企業DB',
        relation: { contains: companyPageId },
      },
      page_size: 5,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Notion 案件DB query error: ${data.message}`);
  return data.results ?? [];
}

/** ドキュメントDB にページを作成し、ページIDを返す */
async function createDocumentPage({ title, companyPageId, casePageId, minutes, tldvUrl }) {
  // 議事録本文を Notion ブロック（paragraph）に変換
  const paragraphBlocks = minutes
    .split('\n')
    .map((line) => ({
      object: 'block',
      type: 'paragraph',
      paragraph: {
        rich_text: [{ type: 'text', text: { content: line } }],
      },
    }))
    .slice(0, 100); // Notion API は一度に 100 ブロックまで

  const body = {
    parent: { database_id: DOCUMENT_DB_ID },
    properties: {
      ドキュメント: {
        title: [{ text: { content: title } }],
      },
      ドキュメント分類: {
        multi_select: [{ name: '社外MTG議事録' }],
      },
      ...(casePageId && {
        案件DB: { relation: [{ id: casePageId }] },
      }),
      ...(companyPageId && {
        企業DB: { relation: [{ id: companyPageId }] },
      }),
      ...(tldvUrl && {
        MTG録画URL: { url: tldvUrl },
      }),
    },
    children: paragraphBlocks,
  };

  const res = await fetch('https://api.notion.com/v1/pages', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.NOTION_TOKEN}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Notion ページ作成エラー: ${data.message}`);
  return data.id;
}

// ─────────────────────────────────────────────────────────────
// Notion ページからタイトルを取得するヘルパー
// ─────────────────────────────────────────────────────────────
function getPageTitle(page) {
  const props = page.properties ?? {};
  for (const prop of Object.values(props)) {
    if (prop.type === 'title' && prop.title?.length > 0) {
      return prop.title.map((t) => t.plain_text).join('');
    }
  }
  return '(名称不明)';
}

// ─────────────────────────────────────────────────────────────
// Claude API ヘルパー
// ─────────────────────────────────────────────────────────────
const anthropic = new Anthropic({ maxRetries: 5 });

/** トランスクリプトから顧客企業名を1つ抽出 */
async function extractCompanyName(transcript) {
  const msg = await anthropic.messages.create({
    model: 'claude-3-haiku-20240307',
    max_tokens: 100,
    messages: [
      {
        role: 'user',
        content: `以下のミーティングトランスクリプトから、「顧客（外部の企業・クライアント）の会社名」を1つだけ抽出してください。
会社名のみを返してください。不明な場合は「不明」と返してください。

トランスクリプト:
${transcript.slice(0, 3000)}`,
      },
    ],
  });
  return msg.content[0].text.trim();
}

/** トランスクリプトと文脈から議事録を生成 */
async function generateMinutes(transcript, companyName, caseName) {
  const systemPrompt = `あなたはCRMシステムへの議事録登録を支援するアシスタントです。
以下のフォーマットで議事録を作成してください：

# 議事録タイトル（日付_ミーティング名）

## 基本情報
- 日時：
- 参加者：
- 目的：

## アジェンダ / 議題

## 議論内容・決定事項

## ネクストアクション（担当者・期限）

## その他・補足

企業名: ${companyName}
案件名: ${caseName}`;

  const msg = await anthropic.messages.create({
    model: 'claude-opus-4-6',
    max_tokens: 2048,
    system: systemPrompt,
    messages: [
      {
        role: 'user',
        content: `以下のトランスクリプトから議事録を作成してください：\n\n${transcript}`,
      },
    ],
  });
  return msg.content[0].text;
}

// ─────────────────────────────────────────────────────────────
// Slack API ヘルパー
// ─────────────────────────────────────────────────────────────

/** response_url に Block Kit メッセージを POST */
async function postToSlack(responseUrl, message) {
  await fetch(responseUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      typeof message === 'string'
        ? { response_type: 'ephemeral', text: message, replace_original: true }
        : { response_type: 'ephemeral', replace_original: true, ...message }
    ),
  });
}

/** chat.postMessage で特定チャンネルにメッセージ送信（view_submission 後に使用） */
async function postMessageToChannel(channelId, message) {
  const payload =
    typeof message === 'string'
      ? { channel: channelId, text: message }
      : { channel: channelId, ...message };

  const res = await fetch('https://slack.com/api/chat.postMessage', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.SLACK_BOT_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!data.ok) console.error('chat.postMessage error:', data);
}

// ─────────────────────────────────────────────────────────────
// Block Kit ビルダー
// ─────────────────────────────────────────────────────────────

/** 企業選択ボタンを含む Block Kit メッセージを生成 */
function buildCompanyBlocks(companies, sessionId, channelId) {
  const buttons = companies.map((page, i) => {
    const name = getPageTitle(page);
    const value = JSON.stringify({
      step: 'company_selected',
      sessionId,
      channelId,
      companyPageId: page.id,
      companyName: name,
    });
    return {
      type: 'button',
      text: { type: 'plain_text', text: `${i + 1}. ${name}` },
      action_id: `select_company_${i}`,
      value: value.slice(0, 2000), // Slack の value 上限
    };
  });

  // 「見つからない / スキップ」ボタン
  const skipValue = JSON.stringify({ step: 'skip', reason: '企業が見つかりませんでした' });
  buttons.push({
    type: 'button',
    text: { type: 'plain_text', text: '🔍 見つからない / スキップ' },
    action_id: 'skip_company',
    value: skipValue,
    style: 'danger',
  });

  return {
    text: '企業を選択してください',
    blocks: [
      {
        type: 'section',
        text: { type: 'mrkdwn', text: '*🏢 企業を選択してください:*' },
      },
      {
        type: 'actions',
        elements: buttons,
      },
    ],
  };
}

/** 案件選択ボタンを含む Block Kit メッセージを生成 */
function buildCaseBlocks(cases, state) {
  const buttons = cases.map((page, i) => {
    const name = getPageTitle(page);
    const value = JSON.stringify({
      step: 'case_selected',
      sessionId: state.sessionId,
      companyPageId: state.companyPageId,
      companyName: state.companyName,
      casePageId: page.id,
      caseName: name,
    });
    return {
      type: 'button',
      text: { type: 'plain_text', text: `${i + 1}. ${name}` },
      action_id: `select_case_${i}`,
      value: value.slice(0, 2000),
    };
  });

  const skipValue = JSON.stringify({ step: 'skip', reason: '案件が見つかりませんでした' });
  buttons.push({
    type: 'button',
    text: { type: 'plain_text', text: '🔍 見つからない / スキップ' },
    action_id: 'skip_case',
    value: skipValue,
    style: 'danger',
  });

  return {
    text: '案件を選択してください',
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*✅ 企業: ${state.companyName}*\n\n*📁 案件を選択してください:*`,
        },
      },
      {
        type: 'actions',
        elements: buttons,
      },
    ],
  };
}

/** 議事録プレビューと確認ボタンを含む Block Kit メッセージを生成 */
function buildMinutesPreviewBlocks(minutesPreview, state) {
  const confirmValue = JSON.stringify({
    step: 'minutes_confirmed',
    companyPageId: state.companyPageId,
    casePageId: state.casePageId,
    minutesSessionId: state.minutesSessionId,
  });

  const skipValue = JSON.stringify({ step: 'skip', reason: 'スキップ' });

  return {
    text: '議事録のプレビューを確認してください',
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*✅ 企業: ${state.companyName}*\n*📁 案件: ${state.caseName}*\n\n*📝 議事録プレビュー（冒頭500文字）:*`,
        },
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `\`\`\`${minutesPreview}\`\`\`\n_全文は Notion 登録後にご確認ください_`,
        },
      },
      {
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: { type: 'plain_text', text: '✅ OK → Notion に登録' },
            action_id: 'confirm_minutes',
            value: confirmValue.slice(0, 2000),
            style: 'primary',
          },
          {
            type: 'button',
            text: { type: 'plain_text', text: '⏭️ スキップ' },
            action_id: 'skip_minutes',
            value: skipValue,
            style: 'danger',
          },
        ],
      },
    ],
  };
}

// ─────────────────────────────────────────────────────────────
// メインハンドラー
// ─────────────────────────────────────────────────────────────
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let payload;
  try {
    payload = JSON.parse(req.body.payload);
  } catch {
    return res.status(400).json({ error: 'Invalid payload' });
  }

  // ─── view_submission: Modal 送信後の処理 ───────────────────
  if (payload.type === 'view_submission') {
    const transcript =
      payload.view?.state?.values?.transcript_block?.transcript_input?.value ?? '';

    let meta = { channelId: null, userId: null };
    try {
      meta = JSON.parse(payload.view?.private_metadata ?? '{}');
    } catch {
      /* ignore */
    }

    if (!transcript.trim()) {
      return res.status(200).json({
        response_action: 'errors',
        errors: { transcript_block: 'トランスクリプトを入力してください' },
      });
    }

    // Slack にすぐ 200 を返してモーダルを閉じる
    res.status(200).json({});

    // waitUntil でレスポンス後も非同期処理を継続
    waitUntil((async () => {
      try {
        // トランスクリプトを Vercel KV に保存（TTL: 24時間）
        const sessionId = randomUUID();
        await kv.set(sessionId, transcript, { ex: 86400 });

        // 企業名を抽出
        const companyName = await extractCompanyName(transcript);

        // 企業DB を検索
        const companies = await queryCompanyDB(companyName);

        if (!meta.channelId) {
          console.error('channelId が private_metadata にありません');
          return;
        }

        if (companies.length === 0) {
          await postMessageToChannel(
            meta.channelId,
            `🔍 企業「${companyName}」は Notion 企業DB に見つかりませんでした。\n処理を終了します。`
          );
          return;
        }

        // 企業選択ボタンをチャンネルに送信
        await postMessageToChannel(
          meta.channelId,
          buildCompanyBlocks(companies, sessionId, meta.channelId)
        );
      } catch (error) {
        console.error('view_submission 処理エラー:', error);
        if (meta.channelId) {
          await postMessageToChannel(meta.channelId, `❌ エラーが発生しました: ${error.message}`);
        }
      }
    })());
    return;
  }

  // ─── block_actions: ボタンクリック処理 ─────────────────────
  if (payload.type === 'block_actions') {
    const action = payload.actions?.[0];
    if (!action) return res.status(200).end();

    let state = {};
    try {
      state = JSON.parse(action.value ?? '{}');
    } catch {
      return res.status(200).end();
    }

    const responseUrl = payload.response_url;

    // 即時 200 を返す（Slack の 3 秒制限対応）
    res.status(200).end();

    // waitUntil でレスポンス後も非同期処理を継続
    waitUntil((async () => {
      // ─── スキップ ─────────────────────────────────────────────
      if (state.step === 'skip') {
        await postToSlack(responseUrl, `⏭️ ${state.reason ?? 'スキップしました。'}\n処理を終了します。`);
        return;
      }

      // ─── 企業選択後 → 案件検索 ───────────────────────────────
      if (state.step === 'company_selected') {
        try {
          const cases = await queryCaseDB(state.companyPageId);

          if (cases.length === 0) {
            await postToSlack(
              responseUrl,
              `✅ 企業: *${state.companyName}*\n\n🔍 案件が見つかりませんでした。\n処理を終了します。`
            );
            return;
          }

          await postToSlack(responseUrl, buildCaseBlocks(cases, state));
        } catch (error) {
          console.error('案件検索エラー:', error);
          await postToSlack(responseUrl, `❌ 案件の検索中にエラーが発生しました: ${error.message}`);
        }
        return;
      }

      // ─── 案件選択後 → 議事録生成 ─────────────────────────────
      if (state.step === 'case_selected') {
        try {
          await postToSlack(
            responseUrl,
            `✅ 企業: *${state.companyName}*\n📁 案件: *${state.caseName}*\n\n⏳ 議事録を生成中です... しばらくお待ちください。`
          );

          // KV からトランスクリプトを取得
          const transcript = await kv.get(state.sessionId);
          if (!transcript) {
            await postToSlack(responseUrl, '❌ セッションが期限切れです。最初からやり直してください。');
            return;
          }

          // Claude で議事録生成
          const minutes = await generateMinutes(transcript, state.companyName, state.caseName);

          // 議事録を KV に保存（TTL: 1 時間）
          const minutesSessionId = randomUUID();
          await kv.set(minutesSessionId, minutes, { ex: 3600 });

          // プレビュー（冒頭 500 文字）
          const minutesPreview = minutes.slice(0, 500) + (minutes.length > 500 ? '...' : '');

          await postToSlack(
            responseUrl,
            buildMinutesPreviewBlocks(minutesPreview, { ...state, minutesSessionId })
          );
        } catch (error) {
          console.error('議事録生成エラー:', error);
          await postToSlack(responseUrl, `❌ 議事録の生成中にエラーが発生しました: ${error.message}`);
        }
        return;
      }

      // ─── 議事録 OK → Notion 登録 ─────────────────────────────
      if (state.step === 'minutes_confirmed') {
        try {
          await postToSlack(responseUrl, '⏳ Notion に議事録を登録中...');

          // KV から議事録を取得
          const minutes = await kv.get(state.minutesSessionId);
          if (!minutes) {
            await postToSlack(
              responseUrl,
              '❌ 議事録データが期限切れです。最初からやり直してください。'
            );
            return;
          }

          // タイトル: 議事録の1行目から取得（例: "# 20260304_建設ドットウェブ商談"）
          const firstLine = minutes.split('\n')[0].replace(/^#+\s*/, '').trim();
          const title = firstLine || `議事録_${new Date().toISOString().slice(0, 10)}`;

          // Notion ドキュメントDB にページ作成
          const pageId = await createDocumentPage({
            title,
            companyPageId: state.companyPageId,
            casePageId: state.casePageId,
            minutes,
            tldvUrl: state.tldvUrl ?? '',
          });

          const pageUrl = `https://notion.so/${pageId.replace(/-/g, '')}`;

          await postToSlack(
            responseUrl,
            `✅ *Notion に議事録を登録しました！*\n\n📄 *${title}*\n🔗 ${pageUrl}`
          );
        } catch (error) {
          console.error('Notion 登録エラー:', error);
          await postToSlack(responseUrl, `❌ Notion への登録中にエラーが発生しました: ${error.message}`);
        }
        return;
      }

      // 未知のステップ
      console.warn('Unknown step:', state.step);
    })());
    return;
  }

  // 未知のペイロードタイプ
  return res.status(200).end();
}
