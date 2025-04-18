// supabase/functions/notifyOnStatusChange/index.ts

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

serve(async (req) => {
  const { record, old_record } = await req.json()

  if (!record || !old_record) {
    return new Response("No record data", { status: 400 })
  }

  const fcmToken = record.fcm_token
  const newStatus = record.status
  const oldStatus = old_record.status

  if (!fcmToken || newStatus === oldStatus) {
    return new Response("No status change or missing token", { status: 200 })
  }

  const messages = {
    next: "You Are Next!",
    ready: "Be Ready!",
    none: "At Ease"
  }

  const statusMessage = messages[newStatus] || "Status Changed"

  const firebaseKey = Deno.env.get("FCM_SERVER_KEY")!
  const response = await fetch("https://fcm.googleapis.com/fcm/send", {
    method: "POST",
    headers: {
      "Authorization": `key=${firebaseKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      to: fcmToken,
      notification: {
        title: "Status Changed",
        body: statusMessage,
        sound: "default"
      }
    })
  })

  const responseBody = await response.text()

  return new Response(`Notification sent with status ${response.status}: ${responseBody}`, {
    status: 200
  })
})
