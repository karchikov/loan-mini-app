export function openTelegramInviteShare(inviteLink) {
  const shareUrl = new URL("https://t.me/share/url");

  shareUrl.searchParams.set("url", inviteLink);
  shareUrl.searchParams.set(
    "text",
    "Присоединяйся ко мне в LoanMiniApp"
  );

  const tg = window.Telegram?.WebApp;

  if (tg?.openTelegramLink) {
    tg.openTelegramLink(shareUrl.toString());
    return;
  }

  if (tg?.openLink) {
    tg.openLink(shareUrl.toString());
    return;
  }

  window.location.href = shareUrl.toString();
}

export async function runTelegramInviteFlow(getInviteLink) {
  const invite = await getInviteLink();

  if (!invite?.invite_link) {
    throw new Error("Invite link was not returned by API");
  }

  openTelegramInviteShare(invite.invite_link);

  return invite;
}