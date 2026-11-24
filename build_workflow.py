"""Builds the LinkedIn Daily Post v2 n8n workflow as JSON.

Run: python build_workflow.py  ->  writes workflow-v2.json next to this file.
Table ids, credential ids, Drive folder ids and the LinkedIn person id are placeholders: fill in your own from n8n.
"""
import json
import os
import uuid
from pathlib import Path

HERE = Path(__file__).parent

TZ = "America/Chicago"
JOSH = os.environ.get("LI_APPROVER_EMAIL", "you@example.com")  # where approval emails go
POSTS = "<li_posts-table-id>"
TOPICS = "<li_topics-table-id>"
TAKES = "<li_takes-table-id>"
# Friday build-log picture drop folder (Joshua's own Drive, shared with the n8n Drive login).
# One picture at a time. After it posts it moves to _used.
PICS = "<drive-folder-id: build-pics>"
PICS_USED = "<drive-folder-id: build-pics/_used>"
GDRIVE = {"googleDriveOAuth2Api": {"id": "<credential-id>", "name": "Google Drive account"}}
OPENAI = {"openAiApi": {"id": "<credential-id>", "name": "OpenAI account"}}
GMAIL = {"gmailOAuth2": {"id": "<credential-id>", "name": "Gmail account"}}
LINKEDIN = {"linkedInOAuth2Api": {"id": "<credential-id>", "name": "LinkedIn account"}}
# Set True to add two webhook test triggers (?day=Tuesday forces a day). Remove after testing.
TEST_HOOKS = False
MODEL = {"__rl": True, "value": "gpt-5.1", "mode": "list", "cachedResultName": "GPT-5.1"}
# v9 (2026-11-20): the four AI steps run on Claude. Set False to go back to GPT-5.1 above.
USE_CLAUDE = True
ANTHROPIC = {"anthropicApi": {"id": "<credential-id>", "name": "Anthropic account"}}
CLAUDE_MODEL = {"__rl": True, "mode": "id", "value": "claude-opus-5-5"}

# ---------------------------------------------------------------- prompts

EXAMPLE_POST = '''"AI will take your job."

Catchy hook for a LinkedIn post or YouTube video.

Most of us have heard some variation of it over the past 6 to 12 months.

"Programmers are obsolete."

"Copywriting is dead."

"Accounting departments won't be needed."

AI is powerful, and the possibilities are probably limitless.

But as the hype begins to calm, one thing is becoming apparent:

AI isn't a human.

AI can code, but a human needs to ensure the code actually solves the right problem.

AI can write copy, but a human needs to verify the tone, voice, and message.

AI can enter data, but a human needs to confirm the data is correct.

AI can analyze information, but a human still needs to determine what the results actually mean.

This is why I think we're moving toward an age where AI expands an individual's daily bandwidth rather than simply replacing them.

One person will be able to accomplish what previously required several.

AI isn't necessarily eliminating the human from the equation.

It's changing how much one human can accomplish.

AI is a multiplier.

The question isn't necessarily:

"Will AI take my job?"

It may be:

"What will I be able to accomplish with AI that I couldn't accomplish before?"

How do you think AI will change your day-to-day work?'''

# His raw build note for 2026-10-30, unedited: how he sounds before any polishing (v7)
OWN_WORDS = '''As I build, explore, and ship more with Claude Code, I am finding more and more things in my personal life that I can automate or improve. A good example is that, in the past, I've always tracked my workouts with a basic Excel sheet. There hasn't been an app I found that I liked or I wanted to pay for, and I hate using Excel, but it was the quickest way to track my progress. Then, Tuesday night, it struck me that I could probably build my own customizable app as a Claude artifact, so I gave it a try. It took Claude less than 20 minutes, and I had my own personalized workout tracker, exactly how I wanted it. I'm thrilled!'''

SYSTEM_WRITER = f'''You write LinkedIn posts for Joshua Mott. Joshua works in AI and has a background in logistics. His audience is mostly logistics and operations people: smart, busy, and mostly new to AI.

Goals: 1) teach real, useful things, no fluff; 2) grow the audience; 3) build Joshua's name as someone who explains AI in logistics clearly.

HARD RULES. Breaking any of these makes the post unusable.
1. Never invent experience. Do not write anything Joshua did, built, tested, saw, measured or learned, and nothing about his employer, team, colleagues, clients or results. No "we tested", "last quarter we", "at my company", "a client of mine", "in my experience". The only exception: things stated in JOSHUA'S TAKE or JOSHUA'S BUILD NOTE, when one is given.
2. Any example must be clearly hypothetical ("Say a broker gets 200 emails a day..."). Never present an example as something that happened. Many posts need no example at all.
3. News facts come only from the NEWS list. Use only what the headline and summary say. Name the source in plain words ("TechCrunch reported..."). Do not invent numbers, quotes, names or details. If a summary is thin, keep the claim small. Do not put any links or URLs in the post. The article link is added at the bottom automatically.
4. No made-up statistics anywhere. If a number is not in NEWS, do not use one.
5. Only refer back to an earlier post if it appears under THIS WEEK'S POSTS, and describe it accurately. Otherwise do not mention earlier posts.
6. Do not repeat a topic, angle or opening line listed under RECENT POSTS. A theme can come back (AI agents in operations is Joshua's strongest), but only with a new angle, a new example and a new opening.
7. Plain text only. No markdown, no asterisks, no bullet symbols, no hashtags, no emojis. Never use em dashes or en dashes: use a comma or a full stop. Lists depend on the content. Use a numbered list, written as "1." on new lines, only when the points really are steps in order or separate items the reader will work through. Otherwise write paragraphs. Never use a list just to give the post structure. No bullet symbols.
8. With JOSHUA'S BUILD NOTE or JOSHUA'S TAKE, keep his words and how he felt. You may fix grammar, trim and reorder. Do not swap his phrases for smarter-sounding ones, do not cut his feelings ("I'm thrilled!"), and do not add a lesson, conclusion or claim he did not make, including in the first line. Build the hook from his own words.
9. Do not sound like the last two weeks. RECENT POSTS show the openings already used. Never use these worn phrases: "Picture a", "Imagine a", "The way I see it", "Here is why", "Here's the thing", "One-line takeaway", "Takeaway:", "on the floor", "this week" as a closing push, "What do you think?". Do not name a source with "X reported that" every time; work the source in naturally.

Voice: write the way Joshua talks when he's explaining something to a sharp colleague over coffee. Plain English, short sentences, mostly short paragraphs with the odd one-line paragraph for emphasis. Talk to the reader as a smart adult who is new to AI, never down to them.
- Conversational, not polished. No clever copywriting lines or neat metaphors (for example "quietly fall into two camps", "a web of choices"). If a line sounds like an ad or a magazine, say it plainer.
- Explain step by step, the way he would walk someone through it: "this happens, then this, then it lands here."
- Use his kind of phrasing only where it fits naturally, one per post at most: "basically", "if that makes sense", "up and running", "knock it out", "to be honest".
- State views as his: "I think", "honestly", "my view is". Vary it. A view on an idea is fine. It is not a claim about his life, so hard rule 1 still applies.
- Down to earth and honest. It's fine to say AI has limits or that people are still figuring it out.
- One exclamation mark is allowed where he'd genuinely be excited. Never more than one.
- No slang (lol, ya), no swearing, no emojis, no hype words (game-changer, revolutionary, unlock, leverage, supercharge, transform).

WHAT MAKES A POST TRAVEL. Joshua's own numbers show his best posts did these things. Do all of them.
1. The hook. Most people only see the first two lines before "see more", so those lines must earn the click. Open with tension: a bold claim, a common belief you are about to knock down, or a concrete scene from a working day. First line under 100 characters. Never open with a definition ("X is how..."), a soft question ("Why do some...") or "Most people think".
2. A point of view. Say plainly what is true about the idea and why. Confident, not hedged, no "it depends" endings. This is a view on ideas, not a claim about Joshua's life, so rule 1 still stands. Two exceptions: a debate post takes no side, and with JOSHUA'S TAKE or JOSHUA'S BUILD NOTE his view stays exactly as he wrote it.
3. Logistics where it fits. Most readers work in logistics and operations, so a real ops angle helps when the topic has one. Do not force it: no dispatcher or TMS example bolted onto a story that has nothing to do with freight. At most one hypothetical example per post.
4. The ending. Vary it. Sometimes a specific question the reader can answer from their own work, sometimes a plain closing line, sometimes just stop when the point is made. Never a labelled takeaway, never just "What do you think?"
5. Sound like a person, not a template. No neat setup, numbered breakdown and summary line. A post can be loose, a little opinionated and end without a bow on it.

Here is a post Joshua wrote himself. Use it for voice only. Do not copy its topic, its lines or its structure.
<<<
{EXAMPLE_POST}
>>>

Here is how Joshua sounds in his own words, unedited. Use it for voice only. Do not copy its topic or its lines.
<<<
{OWN_WORDS}
>>>

Return JSON only, in this shape:
{{"topic":"short label for today's topic","news_title":"exact title of the news item used, or empty","news_url":"its url, or empty","daily_post":"the post text"}}'''

SYSTEM_TREND = '''You help Joshua, who posts about AI for logistics and operations people, pick one trend to give his opinion on.

From the NEWS list, choose the single AI story or trend that his audience would most want an opinion on: something with real consequences for work, that reasonable people could disagree about. Use only facts from the headline and summary. Plain English. Never use em dashes or en dashes.

Return JSON only:
{"trend":"short name, under 10 words","summary":"two plain sentences on what happened, facts from the list only","source":"source name","url":"its url","question":"one direct question asking for Joshua's opinion, under 25 words"}'''

# ---------------------------------------------------------------- code nodes

FEEDS_JS = r'''// News feeds read on every run. Add or remove lines here.
const feeds = [
  'https://techcrunch.com/category/artificial-intelligence/feed/',
  'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
  'https://www.technologyreview.com/topic/artificial-intelligence/feed',
  'https://openai.com/news/rss.xml',
  'https://blog.google/technology/ai/rss/',
  'https://www.freightwaves.com/news/feed',
  'https://www.supplychaindive.com/feeds/news/',
  'https://www.dcvelocity.com/rss/',
];
return feeds.map(url => ({ json: { url } }));
'''

# Shared by "Prepare brief" and "Pick news for take". Plain regex only: new URL() is not
# available in n8n Cloud Code nodes.
NEWS_HELPER_JS = r'''const SOURCES = [
  [/techcrunch\.com/i, 'TechCrunch', 'AI'],
  [/theverge\.com/i, 'The Verge', 'AI'],
  [/technologyreview\.com/i, 'MIT Technology Review', 'AI'],
  [/openai\.com/i, 'OpenAI', 'AI'],
  [/blog\.google/i, 'Google', 'AI'],
  [/freightwaves\.com/i, 'FreightWaves', 'Logistics'],
  [/supplychaindive\.com/i, 'Supply Chain Dive', 'Logistics'],
  [/dcvelocity\.com/i, 'DC Velocity', 'Logistics'],
];
function readNews(nodeName, days, skipUrls) {
  const cutoff = Date.now() - days * 24 * 3600 * 1000;
  const seen = new Set();
  const out = [];
  for (const it of $(nodeName).all()) {
    const j = it.json || {};
    if (!j.link || !j.title) continue;
    const t = Date.parse(j.isoDate || j.pubDate || '');
    if (!t || t < cutoff || seen.has(j.link) || skipUrls.has(j.link)) continue;
    seen.add(j.link);
    const src = SOURCES.find(s => s[0].test(j.link)) || [null, 'News', 'AI'];
    out.push({
      title: String(j.title).replace(/\s+/g, ' ').trim(),
      url: j.link, source: src[1], kind: src[2], t,
      snippet: String(j.contentSnippet || j.content || '').replace(/\s+/g, ' ').trim().slice(0, 240),
    });
  }
  out.sort((a, b) => b.t - a.t);
  return out.filter(n => n.kind === 'AI').slice(0, 20)
    .concat(out.filter(n => n.kind === 'Logistics').slice(0, 8));
}
function newsText(list) {
  if (!list.length) return '';
  return list.map((n, i) => {
    const d = DateTime.fromMillis(n.t).setZone('America/Chicago').toFormat('LLL d');
    return `${i + 1}. [${n.kind}] ${n.title} (${n.source}, ${d}) ${n.url}` + (n.snippet ? `\n   ${n.snippet}` : '');
  }).join('\n');
}
'''

PLAN_JS = r'''// Works out today's post type and length. A test run can force a day with ?day=Tuesday.
const forced = $input.first().json.query?.day;
const now = $now.setZone('America/Chicago');
const day = forced || now.toFormat('cccc');
const pillar = { Monday: 'concept', Tuesday: 'logistics', Wednesday: 'skill', Thursday: 'opinion', Friday: 'myth' }[day];
if (!pillar) throw new Error(`No post planned for ${day}`);

const r = Math.random();
let format;
if (day === 'Thursday') format = r < 0.3 ? 'SHORT' : 'MEDIUM';
// v9.3 (2026-11-22): LONG dropped. The best posts ran 59-160 words, every v7 post ran 168-298.
else format = r < 0.4 ? 'SHORT' : 'MEDIUM';
const specs = {
  SHORT: '60-100 words. One idea, well made. No list. End on a single strong line.',
  MEDIUM: '120-160 words, never more than 160. A hook, then 2-4 short paragraphs. A numbered list only if the content is genuinely steps or separate items.',
};
// v9: a different shape each day so posts stop reading like one template.
const shapes = [
  'STORY: open on one concrete moment or scene and let the point come out of it. No list.',
  'ONE POINT: make a single sharp point, back it up plainly, and stop. No examples beyond one.',
  'PUSHBACK: start from something people commonly say about AI and explain where it is wrong or half right.',
  'WALKTHROUGH: explain it the way Joshua would talk a friend through it, this happens, then this, then this.',
  'HONEST TAKE: what is genuinely good about it, what is overhyped, said straight.',
];
const shape = shapes[Math.floor(Math.random() * shapes.length)];
return [{ json: { day, date: now.toISODate(), pillar, format, spec: specs[format], shape } }];
'''

PREPARE_JS = NEWS_HELPER_JS + r'''
const plan = $('Plan the day').first().json;
const rows = name => $(name).all().map(i => i.json).filter(r => r && r.id !== undefined);
const history = rows('Load post history');
const topics = rows('Load topics');
const takes = rows('Load takes');

const news = readNews('Read feeds', 4, new Set(history.map(h => h.news_url).filter(Boolean)));

// Monday and Wednesday: the least recently used topic from that list, never inside 8 weeks if avoidable.
let topic = '', topic_row_id = '';
if (plan.pillar === 'concept' || plan.pillar === 'skill') {
  const pool = topics.filter(t => t.pillar === plan.pillar);
  const eightWeeksAgo = $now.minus({ weeks: 8 }).toISODate();
  let fresh = pool.filter(t => !t.last_used || t.last_used < eightWeeksAgo);
  if (!fresh.length) fresh = pool;
  const oldest = fresh.map(t => t.last_used || '').sort()[0];
  const tied = fresh.filter(t => (t.last_used || '') === oldest);
  const pick = tied[Math.floor(Math.random() * tied.length)];
  if (pick) { topic = pick.topic; topic_row_id = String(pick.id); }
}

// Thursday: Joshua's reply from Wednesday first, then the opinion bank, else a debate post.
let take = null;
if (plan.pillar === 'opinion') {
  const open = takes.filter(t => t.take && !t.used_on);
  const recent = $now.minus({ days: 2 }).toISODate();
  take = open.filter(t => t.source === 'reply' && (t.for_date || '') >= recent)
      .sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)))[0]
    || open.filter(t => t.source === 'bank')
      .sort((a, b) => String(a.createdAt).localeCompare(String(b.createdAt)))[0]
    || null;
}

// Friday: Joshua's build note from Thursday's email. No note means the usual myth post.
let build = null;
if (plan.day === 'Friday') {
  const recentB = $now.minus({ days: 2 }).toISODate();
  build = takes.filter(t => t.source === 'build' && t.take && !t.used_on && (t.for_date || '') >= recentB)
    .sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)))[0] || null;
}
const pillar = build ? 'build' : plan.pillar;
const note = take || build;

const posted = h => /^posted/.test(h.status || '');
const weekStart = $now.startOf('week').toISODate();
const thisWeek = history.filter(h => posted(h) && h.post_date >= weekStart)
  .sort((a, b) => a.post_date.localeCompare(b.post_date))
  .map(h => `[${h.weekday}]\n${h.draft}`).join('\n\n');
const recent = history.slice(0, 15).map(h =>
  `- ${h.post_date} ${h.weekday} (${h.pillar}) topic: ${h.topic}` +
  (h.news_title ? ` | news: ${h.news_title}` : '') + ` | ${h.status}\n  opened with: ` +
  String(h.draft || '').split('\n')[0].slice(0, 140)).join('\n');

const tasks = {
  concept: `Explain this AI concept: "${topic}". Assume the reader has heard the word but never had it explained. Use at most one example, and only if it makes it clearer. A work example from logistics or operations is good when it fits, but an everyday one is fine too. Leave them able to explain it to a colleague. Only mention a news item if it connects naturally, in one line, with the source.`,
  logistics: `From NEWS, pick the one item with the clearest practical meaning for people in logistics: freight, brokerage, carriers, warehousing, dispatch, customer service, procurement. Prefer AI stories. Say what happened in one or two lines and name the source. Then say what it could actually change for people in logistics, plainly. An example is optional. Be honest about limits, no hype.`,
  skill: `Teach this beginner skill or comparison: "${topic}". Make it practical: what it is, why it matters, and one thing the reader can try today. If it is a comparison, make the difference obvious in plain words. One hypothetical example at most, from operations work if it fits naturally.`,
  opinion: take
    ? `Write a post built around JOSHUA'S TAKE below. His point and his stance are the post. Keep them exactly, and use his own phrases where they work. You may add a hook, structure, and plain-English context about the trend from its news item. Do not add new opinions, predictions, experiences or claims he did not make. Do not make his view stronger or softer than he wrote it.`
    : `Write a debate post. From NEWS, pick one AI trend people genuinely disagree about. Say what happened, naming the source. Lay out the strongest case on each side, fairly, in plain English. End by asking readers where they land. Do not state or hint at Joshua's own position, and do not use "I think" or "I believe".`,
  build: `Write a build log post from JOSHUA'S BUILD NOTE below: what he built or learned this week, in his own words. Keep every fact exactly as he gave it. Do not add results, numbers, time saved, tools, names or claims he did not give. You may explain in plain words what a tool or term means, and say who in logistics or operations could use something like it. Open with the most interesting thing he built, never with "This week I". End with a question that invites readers to say what they would build or automate.`,
  myth: `Bust one common AI myth or misconception that people in logistics and operations believe, ideally one that holds them back at work. If an item in NEWS shows the myth is wrong, use it and name the source. Otherwise argue it plainly. Cover the myth, why people believe it and what is actually true, in flowing paragraphs, not a list. Pick one myth and go deep, do not stack several.`,
};
const labels = { concept: 'AI concept', logistics: 'AI news through a logistics lens', skill: 'Beginner AI skill or comparison', opinion: take ? "Joshua's opinion" : 'Debate post (no opinion from Joshua this week)', myth: 'AI myth or misconception', build: 'Build log (what Joshua built this week)' };

const parts = [
  `TODAY: ${plan.day} ${plan.date}`,
  `POST TYPE: ${labels[pillar]}`,
  `TASK: ${tasks[pillar]}`,
  // v9: a short take from Joshua gets a short post, never padding around it.
  (note && pillar === 'opinion' && String(note.take).split(/\s+/).length < 60)
    ? `FORMAT: SHORT. His take is short, so the post is short: 50-110 words, mostly his words. Do not pad it with context or examples.`
    : `FORMAT: ${plan.format}. ${plan.spec} This is a hard limit. Stop when the format is complete. Do not pad to reach the upper word count.`,
  note ? '' : `SHAPE: ${plan.shape}`,
].filter(Boolean);
if (build) {
  parts.push(`JOSHUA'S BUILD NOTE (his own words, the only personal claims you may use):
"${build.take}"`);
}
if (take) {
  parts.push(`JOSHUA'S TAKE (his own words, the only personal claims you may use):\n"${take.take}"` +
    (take.trend ? `\nTrend it responds to: ${take.trend}${take.trend_url ? ' ' + take.trend_url : ''}` : ''));
}
parts.push(news.length
  ? `NEWS (last 4 days, newest first, not used before):\n${newsText(news)}`
  : `NEWS: none available today. Do not reference any news. Write an evergreen version of today's task.`);
parts.push(`THIS WEEK'S POSTS (only for accurate call-backs):\n${thisWeek || 'None yet.'}`);
parts.push(`RECENT POSTS (do not repeat these topics, angles or openings):\n${recent || 'None yet.'}`);

return [{ json: {
  brief: parts.join('\n\n'),
  topic, topic_row_id,
  pillar,
  take_id: note ? String(note.id) : '',
  take_text: note ? note.take : '',
  take_url: take ? (take.trend_url || '') : '',
  news_count: news.length,
  news: news.map(n => ({ title: n.title, url: n.url })),
} }];
'''


def clean_js(attempt, redraft=False):
    return r'''// Strips dashes, curly quotes and markdown, then checks for invented personal claims.
const ATTEMPT = ''' + str(attempt) + r''';
const REDRAFT = ''' + ("true" if redraft else "false") + r''';
const plan = $('Plan the day').first().json;
const brief = $('Prepare brief').first().json;
const ctx = REDRAFT ? $('Prepare redraft').last().json : {};
const _j = $input.first().json || {};
// GPT puts the text in output[0].content[0].text, Claude in content[0].text (v9 reads both).
const _c = _j.output?.[0]?.content?.[0]?.text ?? (Array.isArray(_j.content) ? _j.content.find(b => b && b.type === 'text')?.text : _j.content) ?? _j.text ?? _j.message?.content;
// Claude can wrap the JSON in a sentence, so keep only the {...} part.
const raw = typeof _c === 'string' && _c.indexOf('{') >= 0 ? _c.slice(_c.indexOf('{'), _c.lastIndexOf('}') + 1) : _c;
let o = raw;
if (typeof raw === 'string') {
  try { o = JSON.parse(raw.replace(/^\s*```(?:json)?/i, '').replace(/```\s*$/, '')); }
  catch (e) { o = { daily_post: raw }; }
}
o = o || {};

let t = String(o.daily_post || '')
  .replace(/(\d)\s*[–—]\s*(\d)/g, '$1-$2')
  .replace(/\s*[–—―]\s*/g, ', ')
  .replace(/[‘’‛]/g, "'").replace(/[“”‟]/g, '"')
  .replace(/[‐‑‒]/g, '-').replace(/ /g, ' ').replace(/…/g, '...')
  .replace(/,\s*([,.!?;:])/g, '$1').replace(/^\s*,\s*/gm, '')
  .replace(/\*\*|__/g, '').replace(/^#+\s*/gm, '')
  .replace(/(^|\s)#[A-Za-z]\w*/g, '$1')
  .replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim();

// If a redraft comes back empty or the AI call fails, keep the last version so the day isn't lost.
const failed = REDRAFT && !t;
if (failed) {
  t = ctx.current_body;
  o = { topic: ctx.topic, news_title: ctx.news_title, news_url: ctx.news_url };
}

// Joshua's own words may hold personal claims: his take, plus any edit notes.
const take = [brief.take_text, ctx.all_notes].filter(Boolean).join(' ').toLowerCase();
const checks = [
  /\b(?:we|i|our team|my team)\s+(?:recently\s+|just\s+|also\s+|actually\s+)?(?:tested|built|deployed|rolled out|implemented|piloted|launched|ran|trialed|trialled|measured|cut|saved|reduced|automated|shipped|replaced)\b/i,
  /\b(?:last|this past)\s+(?:quarter|month|year|week)\b[^.\n]{0,80}\b(?:we|our)\b/i,
  /\b(?:a client of mine|one of my clients|our clients?|our customers?|at my (?:company|job|work)|where i work|my employer|my company)\b/i,
  /\bin my experience\b|\bwhen i worked\b/i,
  /\bmy-employer\b/i,  // your employer's name goes here
];
// A build log is Joshua's own week, so "I built" is allowed there. The other checks still run.
if (brief.pillar === 'build') checks.shift();
const flags = [];
for (const re of checks) {
  const m = t.match(re);
  // The employer's name is never allowed, even if it came from his own words.
  if (m && (/my-employer/i.test(m[0]) || !(take && take.includes(m[0].toLowerCase())))) flags.push(m[0]);
}

// v9: worn phrases and lists that made posts sound the same. First draft only, never on his edits,
// and never when the words came from Joshua himself.
const STOCK = [/\bpicture an?\s/i, /\bimagine an?\s/i, /\bthe way i see it\b/i, /\bone-line takeaway\b/i,
  /^\s*takeaway:/im, /\bhere'?s the thing\b/i, /\bhere is why\b/i];
const style = (ATTEMPT === 1 && !REDRAFT) ? STOCK.map(re => t.match(re))
  .filter(m => m && !(take && take.includes(m[0].trim().toLowerCase()))).map(m => m[0].trim()) : [];

const words = t ? t.split(/\s+/).length : 0;
// v9.3: hard cap. A first draft over 160 words goes back for one rewrite.
const MAX_WORDS = 160;
const tooLong = ATTEMPT === 1 && !REDRAFT && words > MAX_WORDS;
if (tooLong) style.push(`${words} words, over the ${MAX_WORDS} cap`);
// The model sometimes retypes links. Use the exact feed link so the post log stays accurate.
const norm = x => String(x || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const feedNews = brief.news || [];
const match = feedNews.find(n => n.url === o.news_url)
  || feedNews.find(n => o.news_title && norm(n.title) === norm(o.news_title))
  || feedNews.find(n => o.news_title && norm(n.title).slice(0, 40) === norm(o.news_title).slice(0, 40));
const news_title = match ? match.title : (o.news_title || '');
const news_url = match ? match.url : (o.news_url || '');
const topic = o.topic || brief.topic || '';
// Any post built on an article ends with its link, so readers can go read it.
// Only exact feed links (or the link saved with Joshua's take), never one the model typed.
const article_url = match ? match.url : (brief.take_url || '');
const post = article_url && !t.includes(article_url) ? `${t}

Read the article: ${article_url}` : t;

const email = [
  REDRAFT ? `Redraft ${ctx.round}. Your change: "${ctx.note}"` : '',
  failed ? 'THE REDRAFT FAILED, so this is the previous version. Pick Edit it to try again.' : '',
  `${plan.day} post (${plan.format}, ${words} words)`,
  `Type: ${brief.pillar || plan.pillar}${topic ? ' | Topic: ' + topic : ''}`,
  news_title ? `News used: ${news_title}\n${news_url}` : 'News used: none',
  brief.take_text ? `Your words it was built from:\n"${brief.take_text}"` : '',
  flags.length && ATTEMPT > 1 ? `CHECK THIS: the draft still reads like a personal claim: "${flags.join('", "')}". Only post it if it is true.` : '',
  '------------------------------',
  post,
  '------------------------------',
  'Hit the button and pick one. Post it: goes to LinkedIn at a random time between 8:00 and 9:45am Chicago (a few minutes after you choose, if that is later). Edit it: type what to change and a new draft comes back by email. Reject: nothing posts today. No answer by 6pm Chicago time and the day is skipped.',
].filter(Boolean).join('\n\n');

const rewrite_prompt = style.length && !flags.length ? [
  `This LinkedIn draft uses worn phrases or a list that make Joshua's posts sound the same every day: "${style.join('", "')}".`,
  `Rewrite it without them, no "Picture a" example, no labelled takeaway. Say it the plain way Joshua would. Keep the topic, the news item and the facts. ` + (tooLong ? `Cut it to ${MAX_WORDS} words or fewer: keep the one main point and drop the rest.` : `Keep roughly the length.`) + ` Every rule in your instructions still stands.`,
  `Draft:\n${JSON.stringify({ topic, news_title, news_url, daily_post: t })}`,
].join('\n\n') : flags.length ? [
  `This LinkedIn draft states things about Joshua's own experience that he never told us: "${flags.join('", "')}".`,
  `Rewrite it so it makes no claim about anything Joshua, "we", "our team" or "my team" did, built, tested, saw or achieved, and nothing about his employer or clients.`,
  brief.take_text ? `The only personal claims allowed are the ones in his own words: "${brief.take_text}"` : 'No personal claims are allowed at all.',
  `Turn any such story into a clearly hypothetical example ("Say a team..."), or drop it. Keep the topic, the news item, the length and everything else that follows the rules.`,
  style.length ? `Also drop these worn phrases: "${style.join('", "')}".` : '',
  `Draft:\n${JSON.stringify({ topic, news_title, news_url, daily_post: t })}`,
].filter(Boolean).join('\n\n') : '';

return [{ json: { topic, news_title, news_url, daily_post: post, words, flags, style, flagged: flags.length > 0 || style.length > 0, attempt: ATTEMPT, email, rewrite_prompt, round: ctx.round || 0 } }];
'''


NOTE_FIELD = "What should change?"

# Added 2026-11-04 (v8). Reads the approval form. Only the exact fields count, never a search of
# the whole reply, because an edit note can contain any words ("reject", "post with picture").
READ_APPROVAL_JS = r'''const j = $input.first().json || {};
const d = j.data && typeof j.data === 'object' ? j.data : j;
const choice = String(d['Choice'] || '').trim().toLowerCase();
const note = String(d[''' + json.dumps(NOTE_FIELD) + r'''] || '').trim();
let edit = choice === 'edit it';
let approved = ['post it', 'post with picture', 'post text only'].includes(choice);
// Words in the box mean he wants changes, so never post over them.
if (approved && note) { approved = false; edit = true; }
const with_picture = approved && choice === 'post with picture';
const rejected = choice === 'reject';
return [{ json: { approved, with_picture, rejected, edit, note } }];
'''

PREPARE_REDRAFT_JS = r'''// Builds the redraft request from the saved draft and Joshua's edit note.
const row = $input.first().json;
const note = $('Read approval').last().json.note;
const brief = $('Prepare brief').first().json;
const old = String(row.edit_notes || '');
const round = (old.match(/^Round \d+:/gm) || []).length + 1;
const all_notes = (old ? old + '\n' : '') + `Round ${round}: ${note}`;
// The article link is added back in code after the redraft.
const current_body = String(row.draft || '').replace(/\n*Read the article: \S+\s*$/, '').trim();
const prompt = [
  'Joshua read this LinkedIn draft and wants changes.',
  `CURRENT DRAFT:\n<<<\n${current_body}\n>>>`,
  `CURRENT DETAILS: topic: ${row.topic || 'none'} | news_title: ${row.news_title || 'none'} | news_url: ${row.news_url || 'none'}`,
  `JOSHUA'S EDIT NOTE (his own words):\n"${note}"`,
  old ? `His earlier notes on this post, which still apply:\n${old}` : '',
  `HOW TO APPLY THE NOTE:
1. Do exactly what the note asks.
2. If it asks for a small change, change only that and keep every other line word for word. Do not improve lines he did not mention.
3. If it asks for a rewrite or a new topic, write a fresh post on what he asked for.
4. Keep about the same length unless he asks otherwise.
5. Anything he says about himself in the note is true. Treat it as JOSHUA'S TAKE under hard rules 1 and 8. Add nothing else about him.
6. Every other hard rule still stands. Facts about news come only from his note or the NEWS list below.
7. Return the same topic, news_title and news_url unless the post now uses something different. If it no longer uses a news item, return them empty.`,
  `ORIGINAL BRIEF (background and the NEWS list. His note overrides its task and format):\n${brief.brief}`,
].filter(Boolean).join('\n\n');
return [{ json: { prompt, note, all_notes, round, current_body, topic: row.topic || '', news_title: row.news_title || '', news_url: row.news_url || '' } }];
'''


PICK_TAKE_JS = NEWS_HELPER_JS + r'''
const news = readNews('Read feeds (take)', 5, new Set());
return [{ json: {
  news_text: news.length ? `NEWS (last 5 days, newest first):\n${newsText(news)}` : '',
  for_date: $now.setZone('America/Chicago').plus({ days: 1 }).toISODate(),
} }];
'''

# Added 2026-10-19. Posting the moment Josh approved dropped reach, so posts now go out
# at a random time inside his audience's best window (8:00-9:45 Chicago, tightened 2026-10-22).
PICK_POST_TIME_JS = r'''// Picks a random post time inside the 8:00-9:45 Chicago window.
// $now uses the workflow timezone (America/Chicago).
const now = $now;
const start = now.set({ hour: 8, minute: 0, second: 0, millisecond: 0 });
const end = now.set({ hour: 9, minute: 45, second: 0, millisecond: 0 });

const rand = (a, b) => a + Math.random() * (b - a);
let postAt;

if (now < start) {
  // Approved early: anywhere in the window
  postAt = start.plus({ milliseconds: rand(0, end.diff(start).as('milliseconds')) });
} else if (now < end.minus({ minutes: 10 })) {
  // Approved inside the window: somewhere between 3 minutes from now and 9:45
  const from = now.plus({ minutes: 3 });
  postAt = from.plus({ milliseconds: rand(0, end.diff(from).as('milliseconds')) });
} else {
  // Approved late: short random delay so it still looks hand-posted
  postAt = now.plus({ minutes: rand(3, 12) });
}

return [{ json: { postAt: postAt.toISO(), postAtLocal: postAt.toFormat('h:mm a'), with_picture: $input.first().json.with_picture === true } }];
'''


# ---------------------------------------------------------------- node helpers

nodes = []
connections = {}


def node(name, ntype, version, params, pos, **extra):
    n = {"id": str(uuid.uuid4()), "name": name, "type": ntype, "typeVersion": version,
         "position": pos, "parameters": params}
    n.update(extra)
    nodes.append(n)
    return name


def link(src, dst, out=0):
    outs = connections.setdefault(src, {"main": []})["main"]
    while len(outs) <= out:
        outs.append([])
    outs[out].append({"node": dst, "type": "main", "index": 0})


def code(name, js, pos, **extra):
    return node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


def table_ref(tid):
    return {"__rl": True, "mode": "id", "value": tid}


def schema(cols):
    return [{"id": c, "displayName": c, "required": False, "defaultMatch": False, "display": True,
             "type": "string", "canBeUsedToMatch": True} for c in cols]


def table_get(name, tid, pos, limit=None):
    p = {"resource": "row", "operation": "get", "dataTableId": table_ref(tid), "filters": {}}
    if limit:
        p.update({"returnAll": False, "limit": limit, "orderBy": True,
                  "orderByColumn": "createdAt", "orderByDirection": "DESC"})
    else:
        p["returnAll"] = True
    return node(name, "n8n-nodes-base.dataTable", 1.1, p, pos, executeOnce=True, alwaysOutputData=True)


def table_get_row(name, tid, row_id_expr, pos):
    return node(name, "n8n-nodes-base.dataTable", 1.1, {
        "resource": "row", "operation": "get", "dataTableId": table_ref(tid),
        "matchType": "allConditions",
        "filters": {"conditions": [{"keyName": "id", "condition": "eq", "keyValue": row_id_expr}]},
        "returnAll": True}, pos)


def table_insert(name, tid, values, pos):
    return node(name, "n8n-nodes-base.dataTable", 1.1, {
        "resource": "row", "operation": "insert", "dataTableId": table_ref(tid),
        "columns": {"mappingMode": "defineBelow", "value": values, "schema": schema(values)},
        "options": {}}, pos)


def table_update(name, tid, row_id_expr, values, pos):
    return node(name, "n8n-nodes-base.dataTable", 1.1, {
        "resource": "row", "operation": "update", "dataTableId": table_ref(tid),
        "matchType": "allConditions",
        "filters": {"conditions": [{"keyName": "id", "condition": "eq", "keyValue": row_id_expr}]},
        "columns": {"mappingMode": "defineBelow", "value": values, "schema": schema(values)},
        "options": {}}, pos)


def openai(name, system, user_expr, pos, **extra):
    if USE_CLAUDE:
        return node(name, "@n8n/n8n-nodes-langchain.anthropic", 1, {
            "resource": "text", "operation": "message", "modelId": CLAUDE_MODEL,
            "messages": {"values": [{"role": "user", "content": user_expr}]},
            "simplify": True,
            "options": {"system": system, "maxTokens": 4000}}, pos, credentials=ANTHROPIC, **extra)
    return node(name, "@n8n/n8n-nodes-langchain.openAi", 2.3, {
        "modelId": MODEL,
        "responses": {"values": [{"role": "system", "content": system}, {"content": user_expr}]},
        "builtInTools": {},
        "options": {"textFormat": {"textOptions": {"type": "json_object"}}}}, pos, credentials=OPENAI, **extra)


def if_true(name, expr, pos):
    return node(name, "n8n-nodes-base.if", 2.2, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"id": str(uuid.uuid4()), "leftValue": expr, "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
            "combinator": "and"},
        "options": {}}, pos)


def schedule(name, cron, pos):
    return node(name, "n8n-nodes-base.scheduleTrigger", 1.2,
                {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}}, pos)


def rss(name, pos):
    return node(name, "n8n-nodes-base.rssFeedRead", 1.2, {"url": "={{ $json.url }}", "options": {}},
                pos, onError="continueRegularOutput")


def webhook(name, pos):
    hook = str(uuid.uuid4())
    return node(name, "n8n-nodes-base.webhook", 2,
                {"httpMethod": "GET", "path": hook, "responseMode": "onReceived", "options": {}},
                pos, webhookId=hook)


# ---------------------------------------------------------------- daily post flow

X = 0
schedule("Weekdays 7am", "0 7 * * 1-5", [X, 0])
if TEST_HOOKS:
    webhook("Test run", [X, 180])
code("Plan the day", PLAN_JS, [X + 220, 80])
table_get("Load post history", POSTS, [X + 440, 80], limit=15)
table_get("Load topics", TOPICS, [X + 660, 80])
table_get("Load takes", TAKES, [X + 880, 80])
code("Feed list", FEEDS_JS, [X + 1100, 80], executeOnce=True)
rss("Read feeds", [X + 1320, 80])
code("Prepare brief", PREPARE_JS, [X + 1540, 80])
openai("Write draft", SYSTEM_WRITER, "={{ $json.brief }}", [X + 1760, 80])
code("Clean and check", clean_js(1), [X + 1980, 80])
if_true("Needs rewrite?", "={{ $json.flagged }}", [X + 2200, 80])
openai("Rewrite without claims", SYSTEM_WRITER, "={{ $json.rewrite_prompt }}", [X + 2420, -60])
code("Clean rewrite", clean_js(2), [X + 2640, -60])
table_insert("Log draft", POSTS, {
    "post_date": "={{ $('Plan the day').first().json.date }}",
    "weekday": "={{ $('Plan the day').first().json.day }}",
    "pillar": "={{ $('Prepare brief').first().json.pillar }}",
    "topic": "={{ $json.topic }}",
    "news_title": "={{ $json.news_title }}",
    "news_url": "={{ $json.news_url }}",
    "take_used": "={{ $('Prepare brief').first().json.take_text }}",
    "draft": "={{ $json.daily_post }}",
    "status": "pending",
}, [X + 2860, 80])
# 6pm Chicago, or an hour from now if a late run would otherwise time out at once.
APPROVE_BY = {"values": {
    "limitType": "atSpecifiedTime",
    "maxDateAndTime": "={{ $now.setZone('America/Chicago').set({ hour: 18, minute: 0, second: 0 }) > $now.plus({ hours: 1 }) ? $now.setZone('America/Chicago').set({ hour: 18, minute: 0, second: 0 }).toISO() : $now.plus({ hours: 1 }).toISO() }}"}}
APPROVE_SUBJECT = "=LinkedIn draft for approval - {{ $('Plan the day').first().json.day }} {{ $('Plan the day').first().json.date }}{{ $json.round ? ' (redraft ' + $json.round + ')' : '' }}"
NOTE_FORM_FIELD = {"fieldLabel": NOTE_FIELD, "fieldType": "textarea", "requiredField": False,
                   "placeholder": "Only for Edit it. Example: make the hook shorter and drop the last paragraph."}


def drive_http(name, method, url, pos, query=None, file_out=False, **extra):
    """Drive API call through the saved Google Drive login."""
    p = {"method": method, "url": url, "authentication": "predefinedCredentialType",
         "nodeCredentialType": "googleDriveOAuth2Api", "options": {}}
    if query:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query.items()]}
    if file_out:
        p["options"] = {"response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}}
    return node(name, "n8n-nodes-base.httpRequest", 4.2, p, pos, credentials=GDRIVE, **extra)


# Friday only: offer the one picture waiting in build-pics. A Drive error just means no picture.
drive_http("Find picture", "GET", "https://www.googleapis.com/drive/v3/files", [X + 3080, 80], query={
    "q": f"'{PICS}' in parents and trashed = false and mimeType contains 'image/'",
    "fields": "files(id,name,mimeType,webViewLink)", "orderBy": "createdTime desc",
    "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"},
    onError="continueRegularOutput", alwaysOutputData=True)
code("Pick picture", r"""const plan = $('Plan the day').first().json;
const files = ($input.first()?.json?.files || []).filter(f => String(f.mimeType || '').startsWith('image/'));
const f = plan.day === 'Friday' ? files[0] : null;
const email = $('Clean rewrite').isExecuted ? $('Clean rewrite').first().json.email : $('Clean and check').first().json.email;
return [{ json: { has_picture: !!f, picture_id: f?.id || '', picture_name: f?.name || '', picture_link: f?.webViewLink || '', email, round: 0 } }];
""", [X + 3300, 80])
if_true("Got picture?", "={{ $json.has_picture }}", [X + 3520, 80])
node("Ask Josh to approve", "n8n-nodes-base.gmail", 2.1, {
    "resource": "message", "operation": "sendAndWait",
    "sendTo": JOSH,
    "subject": APPROVE_SUBJECT,
    "message": "={{ $json.email }}",
    "responseType": "customForm",
    "formFields": {"values": [{"fieldLabel": "Choice", "fieldType": "dropdown", "requiredField": True,
                               "fieldOptions": {"values": [{"option": "Post it"},
                                                           {"option": "Edit it"},
                                                           {"option": "Reject"}]}},
                              NOTE_FORM_FIELD]},
    "options": {"messageButtonLabel": "Post, edit or reject", "responseFormTitle": "Today's post",
                "responseFormButtonLabel": "Send", "limitWaitTime": APPROVE_BY, "appendAttribution": False},
}, [X + 3740, 200], webhookId=str(uuid.uuid4()), credentials=GMAIL)
node("Ask Josh to approve (picture)", "n8n-nodes-base.gmail", 2.1, {
    "resource": "message", "operation": "sendAndWait",
    "sendTo": JOSH,
    "subject": APPROVE_SUBJECT,
    "message": "={{ $json.email + '\\n\\nPICTURE WAITING: ' + $('Pick picture').first().json.picture_name + '\\n' + $('Pick picture').first().json.picture_link + '\\nOpen it first. Only post it if it shows no client names, emails, keys or employer screens. Text only leaves it in the folder for next time.' }}",
    "responseType": "customForm",
    "formFields": {"values": [{"fieldLabel": "Choice", "fieldType": "dropdown", "requiredField": True,
                               "fieldOptions": {"values": [{"option": "Post with picture"},
                                                           {"option": "Post text only"},
                                                           {"option": "Edit it"},
                                                           {"option": "Reject"}]}},
                              NOTE_FORM_FIELD]},
    "options": {"messageButtonLabel": "Post, edit or reject", "responseFormTitle": "Friday post",
                "responseFormButtonLabel": "Send", "limitWaitTime": APPROVE_BY, "appendAttribution": False},
}, [X + 3740, -40], webhookId=str(uuid.uuid4()), credentials=GMAIL)
code("Read approval", READ_APPROVAL_JS, [X + 3960, 80])
if_true("Approved?", "={{ $json.approved === true }}", [X + 4180, 80])
code("Pick Post Time", PICK_POST_TIME_JS, [X + 4400, 0])
node("Wait For Post Time", "n8n-nodes-base.wait", 1.1,
     {"resume": "specificTime", "dateTime": "={{ $json.postAt }}"},
     [X + 4620, 0], webhookId=str(uuid.uuid4()))
if_true("Picture post?", "={{ $('Pick Post Time').first().json.with_picture === true }}", [X + 4840, 0])
drive_http("Download picture", "GET",
           "=https://www.googleapis.com/drive/v3/files/{{ $('Pick picture').first().json.picture_id }}?alt=media&supportsAllDrives=true",
           [X + 5060, -120], file_out=True, onError="continueErrorOutput")
node("Post to LinkedIn (picture)", "n8n-nodes-base.linkedIn", 1, {
    "person": "<linkedin-person-id>",
    "text": "={{ $('Load final draft').first().json.draft }}",
    "shareMediaCategory": "IMAGE",
    "binaryPropertyName": "data",
    "additionalFields": {"visibility": "PUBLIC"}}, [X + 5280, -120], credentials=LINKEDIN,
    onError="continueErrorOutput")
node("Post to LinkedIn", "n8n-nodes-base.linkedIn", 1, {
    "person": "<linkedin-person-id>",
    "text": "={{ $('Load final draft').first().json.draft }}",
    "additionalFields": {"visibility": "PUBLIC"}}, [X + 5280, 80], credentials=LINKEDIN)
drive_http("Move picture to used", "PATCH",
           "=https://www.googleapis.com/drive/v3/files/{{ $('Pick picture').first().json.picture_id }}",
           [X + 5500, -240], query={"addParents": PICS_USED, "removeParents": PICS, "supportsAllDrives": "true"},
           onError="continueRegularOutput")
table_update("Mark posted", POSTS, "={{ $('Log draft').first().json.id }}",
             {"status": "posted"}, [X + 5500, 0])
table_update("Mark topic used", TOPICS, "={{ $('Prepare brief').first().json.topic_row_id || '0' }}",
             {"last_used": "={{ $('Plan the day').first().json.date }}"}, [X + 5720, -80])
table_update("Mark take used", TAKES, "={{ $('Prepare brief').first().json.take_id || '0' }}",
             {"used_on": "={{ $('Plan the day').first().json.date }}"}, [X + 5720, 80])
table_update("Mark rejected or skipped", POSTS, "={{ $('Log draft').first().json.id }}",
             {"status": "={{ $json.rejected ? 'rejected' : 'skipped (no reply)' }}"},
             [X + 4400, 200])

# Make room for the two new steps in the main line, then add the edit loop above it (v8, 2026-11-04).
for n in nodes:
    if n["position"][0] >= X + 4180:
        n["position"][0] += 440
    elif n["position"][0] >= X + 3520:
        n["position"][0] += 220
node("Draft to send", "n8n-nodes-base.noOp", 1, {}, [X + 3520, 80])
if_true("Edit?", "={{ $json.edit === true }}", [X + 4400, 80])
if_true("Note given?", "={{ $json.note.length > 0 }}", [X + 4400, -140])
code("Ask again", r"""// He picked Edit but typed nothing, so resend the same draft with a reminder.
const NUDGE = 'You picked Edit it but the box was empty, so nothing changed. Here is the same draft again.\n\n';
const prev = $('Draft to send').last().json;
return [{ json: { ...prev, email: NUDGE + String(prev.email).replace(NUDGE, '') } }];
""", [X + 4180, -140])
table_get_row("Load draft to edit", POSTS, "={{ $('Log draft').first().json.id }}", [X + 4400, -300])
code("Prepare redraft", PREPARE_REDRAFT_JS, [X + 4180, -300])
openai("Write redraft", SYSTEM_WRITER, "={{ $json.prompt }}", [X + 3960, -300], onError="continueRegularOutput")
code("Clean redraft", clean_js(2, redraft=True), [X + 3740, -300])
table_update("Save redraft", POSTS, "={{ $('Log draft').first().json.id }}", {
    "topic": "={{ $json.topic }}",
    "news_title": "={{ $json.news_title }}",
    "news_url": "={{ $json.news_url }}",
    "draft": "={{ $json.daily_post }}",
    "edit_notes": "={{ $('Prepare redraft').last().json.all_notes }}",
}, [X + 3520, -300])
code("Redraft ready", r"""const c = $('Clean redraft').last().json;
return [{ json: { ...$('Pick picture').first().json, email: c.email, round: c.round } }];
""", [X + 3520, -140])
# What gets posted is read fresh from li_posts, so it is always the latest redraft.
table_get_row("Load final draft", POSTS, "={{ $('Log draft').first().json.id }}", [X + 5170, 160])

for a, b in [("Weekdays 7am", "Plan the day"),
             ("Plan the day", "Load post history"), ("Load post history", "Load topics"),
             ("Load topics", "Load takes"), ("Load takes", "Feed list"), ("Feed list", "Read feeds"),
             ("Read feeds", "Prepare brief"), ("Prepare brief", "Write draft"),
             ("Write draft", "Clean and check"), ("Clean and check", "Needs rewrite?"),
             ("Rewrite without claims", "Clean rewrite"), ("Clean rewrite", "Log draft"),
             ("Log draft", "Find picture"), ("Find picture", "Pick picture"), ("Pick picture", "Draft to send"),
             ("Draft to send", "Got picture?"),
             ("Ask Josh to approve", "Read approval"), ("Ask Josh to approve (picture)", "Read approval"),
             ("Read approval", "Edit?"),
             ("Ask again", "Draft to send"),
             ("Load draft to edit", "Prepare redraft"), ("Prepare redraft", "Write redraft"),
             ("Write redraft", "Clean redraft"), ("Clean redraft", "Save redraft"),
             ("Save redraft", "Redraft ready"), ("Redraft ready", "Draft to send"),
             ("Pick Post Time", "Wait For Post Time"), ("Wait For Post Time", "Load final draft"),
             ("Load final draft", "Picture post?"),
             ("Post to LinkedIn", "Mark posted"), ("Mark posted", "Mark topic used"),
             ("Mark posted", "Mark take used")]:
    link(a, b)
if TEST_HOOKS:
    link("Test run", "Plan the day")
    link("Test take request", "Feed list (take)")
    link("Test build request", "Build ask")
link("Needs rewrite?", "Rewrite without claims", 0)
link("Needs rewrite?", "Log draft", 1)
link("Got picture?", "Ask Josh to approve (picture)", 0)
link("Got picture?", "Ask Josh to approve", 1)
link("Edit?", "Note given?", 0)
link("Edit?", "Approved?", 1)
link("Note given?", "Load draft to edit", 0)
link("Note given?", "Ask again", 1)
link("Approved?", "Pick Post Time", 0)
link("Approved?", "Mark rejected or skipped", 1)
link("Picture post?", "Download picture", 0)
link("Picture post?", "Post to LinkedIn", 1)
# A failed download or picture post falls back to the text-only post, so the day is never lost.
link("Download picture", "Post to LinkedIn (picture)", 0)
link("Download picture", "Post to LinkedIn", 1)
link("Post to LinkedIn (picture)", "Mark posted", 0)
link("Post to LinkedIn (picture)", "Move picture to used", 0)
link("Post to LinkedIn (picture)", "Post to LinkedIn", 1)

# ---------------------------------------------------------------- Wednesday "your take" flow

Y = 520
schedule("Wednesdays 9am", "0 9 * * 3", [X, Y])
if TEST_HOOKS:
    webhook("Test take request", [X, Y + 180])
code("Feed list (take)", FEEDS_JS, [X + 220, Y + 80])
rss("Read feeds (take)", [X + 440, Y + 80])
code("Pick news for take", PICK_TAKE_JS, [X + 660, Y + 80])
openai("Choose the trend", SYSTEM_TREND, "={{ $json.news_text }}", [X + 880, Y + 80])
code("Read trend", r'''const _j = $input.first().json || {};
// GPT puts the text in output[0].content[0].text, Claude in content[0].text (v9 reads both).
const _c = _j.output?.[0]?.content?.[0]?.text ?? (Array.isArray(_j.content) ? _j.content.find(b => b && b.type === 'text')?.text : _j.content) ?? _j.text ?? _j.message?.content;
// Claude can wrap the JSON in a sentence, so keep only the {...} part.
const raw = typeof _c === 'string' && _c.indexOf('{') >= 0 ? _c.slice(_c.indexOf('{'), _c.lastIndexOf('}') + 1) : _c;
let o = raw;
if (typeof raw === 'string') { try { o = JSON.parse(raw.replace(/^\s*```(?:json)?/i, '').replace(/```\s*$/, '')); } catch (e) { o = {}; } }
o = o || {};
const fix = s => String(s || '').replace(/\s*[–—]\s*/g, ', ').replace(/[‘’]/g, "'").replace(/[“”]/g, '"').trim();
const trend = fix(o.trend), summary = fix(o.summary), source = fix(o.source), url = String(o.url || '');
const question = fix(o.question) || `What's your take on ${trend}?`;
const message = [
  `This week's trend: ${trend}`,
  summary,
  source || url ? `Source: ${source} ${url}`.trim() : '',
  question,
  'Hit the button and type 1 to 3 rough sentences. Typos are fine. Your words become Thursday\'s post, and nothing gets added that you did not say.',
  'No reply by Thursday 6:55am and Thursday uses your opinion bank, or a debate post that takes no side.',
].filter(Boolean).join('\n\n');
return [{ json: { trend, summary, source, url, question, message, for_date: $('Pick news for take').first().json.for_date } }];
''', [X + 1100, Y + 80])
node("Ask Josh for his take", "n8n-nodes-base.gmail", 2.1, {
    "resource": "message", "operation": "sendAndWait",
    "sendTo": JOSH,
    "subject": "=Thursday post: your take on {{ $json.trend }}?",
    "message": "={{ $json.message }}",
    "responseType": "freeText",
    "options": {
        "messageButtonLabel": "Give my take",
        "responseFormTitle": "Your take for Thursday",
        "responseFormDescription": "={{ $json.trend }}: {{ $json.question }}",
        "responseFormButtonLabel": "Send",
        "limitWaitTime": {"values": {
            "limitType": "atSpecifiedTime",
            "maxDateAndTime": "={{ $now.setZone('America/Chicago').plus({ days: 1 }).set({ hour: 6, minute: 55, second: 0 }).toISO() }}"}},
        "appendAttribution": False},
}, [X + 1320, Y + 80], webhookId=str(uuid.uuid4()), credentials=GMAIL)
if_true("Replied?", "={{ String($json.data?.text || '').trim().length > 0 }}", [X + 1540, Y + 80])
table_insert("Save take", TAKES, {
    "take": "={{ String($json.data.text).trim() }}",
    "source": "reply",
    "trend": "={{ $('Read trend').first().json.trend }}",
    "trend_url": "={{ $('Read trend').first().json.url }}",
    "for_date": "={{ $('Read trend').first().json.for_date }}",
    "used_on": "",
}, [X + 1760, Y])

for a, b in [("Wednesdays 9am", "Feed list (take)"),
             ("Feed list (take)", "Read feeds (take)"), ("Read feeds (take)", "Pick news for take"),
             ("Pick news for take", "Choose the trend"), ("Choose the trend", "Read trend"),
             ("Read trend", "Ask Josh for his take"), ("Ask Josh for his take", "Replied?")]:
    link(a, b)
link("Replied?", "Save take", 0)

# ---------------------------------------------------------------- Thursday "what did you build" flow

Z = 1040
schedule("Thursdays 2pm", "0 14 * * 4", [X, Z])
if TEST_HOOKS:
    webhook("Test build request", [X, Z + 180])
code("Build ask", r"""const friday = $now.setZone('America/Chicago').plus({ days: 1 }).toISODate();
const message = [
  'What did you build or learn this week?',
  "Hit the button and type 2 or 3 rough lines. Typos are fine. Your words become Friday's post, and nothing gets added that you did not say.",
  'Got a screenshot? Drop ONE picture in My Drive/LinkedIn/build-pics before Friday 7am and the approval email will offer it. Check it shows no client names, emails, keys or employer screens.',
  'No reply by Friday 6:55am and Friday is a myth post.',
].join('\n\n');
return [{ json: { for_date: friday, message } }];
""", [X + 220, Z + 80])
node("Ask Josh what he built", "n8n-nodes-base.gmail", 2.1, {
    "resource": "message", "operation": "sendAndWait",
    "sendTo": JOSH,
    "subject": "Friday post: what did you build this week?",
    "message": "={{ $json.message }}",
    "responseType": "freeText",
    "options": {
        "messageButtonLabel": "Tell it what I built",
        "responseFormTitle": "Your build log for Friday",
        "responseFormDescription": "What you built or learned this week, in your own words.",
        "responseFormButtonLabel": "Send",
        "limitWaitTime": {"values": {
            "limitType": "atSpecifiedTime",
            "maxDateAndTime": "={{ $now.setZone('America/Chicago').plus({ days: 1 }).set({ hour: 6, minute: 55, second: 0 }).toISO() }}"}},
        "appendAttribution": False},
}, [X + 440, Z + 80], webhookId=str(uuid.uuid4()), credentials=GMAIL)
if_true("Built reply?", "={{ String($json.data?.text || '').trim().length > 0 }}", [X + 660, Z + 80])
table_insert("Save build note", TAKES, {
    "take": "={{ String($json.data.text).trim() }}",
    "source": "build",
    "trend": "",
    "trend_url": "",
    "for_date": "={{ $('Build ask').first().json.for_date }}",
    "used_on": "",
}, [X + 880, Z])

for a, b in [("Thursdays 2pm", "Build ask"), ("Build ask", "Ask Josh what he built"),
             ("Ask Josh what he built", "Built reply?")]:
    link(a, b)
link("Built reply?", "Save build note", 0)

# ---------------------------------------------------------------- notes on the canvas

node("Note", "n8n-nodes-base.stickyNote", 1, {"width": 520, "height": 300, "content": (
    "## LinkedIn Daily Post v2\n"
    "Mon concept, Tue news for logistics, Wed beginner skill, Thu Joshua's take, "
    "Fri build log (asked Thu 2pm, myth if no reply).\n"
    "Friday picture: drop ONE image in My Drive/LinkedIn/build-pics. It moves to _used once posted.\n\n"
    "Topics: data table li_topics (pillar = concept or skill). Add rows any time.\n"
    "Opinion bank: data table li_takes, source = bank, leave used_on empty.\n"
    "History: li_posts. Every draft is logged with its status. Edit notes are saved in edit_notes.\n\n"
    "Edit it: your note goes back to the writer and a new draft is emailed. Repeats until 6pm.\n"
    "Nothing posts unless you choose to post. No reply by 6pm and the day is skipped.")},
    [X - 40, -420])

workflow = {
    "name": "LinkedIn Daily Post v2",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1", "timezone": TZ, "callerPolicy": "workflowsFromSameOwner"},
}
(HERE / "workflow-v2.json").write_text(json.dumps(workflow, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{len(nodes)} nodes written")
