"""
Slack API connector for Weaver AI
Fetches message history from Slack channels
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import get_settings

settings = get_settings()

class SlackConnector:
    """Handles Slack API interactions and data fetching"""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize Slack client with bot token"""
        self.token = token or settings.SLACK_BOT_TOKEN
        if not self.token:
            raise ValueError("Slack bot token is required. Set SLACK_BOT_TOKEN environment variable.")
        
        self.client = WebClient(token=self.token)
        self.user_cache = {}  # Cache for user ID to name mapping
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Slack API connection and get bot info"""
        try:
            response = self.client.auth_test()
            if response and hasattr(response, 'data') and response.data:
                user = response.data.get('user', 'Unknown') if isinstance(response.data, dict) else 'Unknown'
                print(f"✅ Connected to Slack as: {user}")
                return response.data if isinstance(response.data, dict) else {}
            else:
                user = response.get('user', 'Unknown') if response and isinstance(response, dict) else 'Unknown'
                print(f"✅ Connected to Slack as: {user}")
                return response if isinstance(response, dict) else {}
        except SlackApiError as e:
            error_msg = e.response.get('error', 'Unknown error') if e.response else 'Unknown error'
            raise Exception(f"Failed to connect to Slack: {error_msg}")
    
    def get_user_info(self, user_id: str) -> str:
        """Get user display name from user ID (with caching)"""
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            response = self.client.users_info(user=user_id)
            if response and response.get('user'):
                user_info = response['user']
                if user_info:
                    user_name = user_info.get('real_name') or user_info.get('name', user_id)
                    self.user_cache[user_id] = user_name
                    return user_name
            
            # Fallback if user info not available
            self.user_cache[user_id] = user_id
            return user_id
        except SlackApiError:
            # Fallback to user ID if lookup fails
            self.user_cache[user_id] = user_id
            return user_id
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels the bot has access to"""
        try:
            channels = []
            cursor = None
            
            while True:
                response = self.client.conversations_list(
                    cursor=cursor,
                    types="public_channel,private_channel",
                    limit=100
                )
                
                if not response or not response.get('channels'):
                    break
                
                channels_data = response.get('channels', [])
                if channels_data:
                    for channel in channels_data:
                        channels.append({
                            "id": channel['id'],
                            "name": channel['name'],
                            "is_private": channel['is_private'],
                            "member_count": channel.get('num_members', 0)
                        })
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            
            return channels
        except SlackApiError as e:
            raise Exception(f"Failed to fetch channels: {e.response['error']}")
    
    def fetch_channel_messages(self, channel_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch messages from a specific channel"""
        print(f"📥 Fetching messages from channel {channel_id}...")
        
        try:
            messages = []
            cursor = None
            fetched_count = 0
            
            while fetched_count < limit:
                # Calculate how many messages to fetch in this batch
                batch_limit = min(200, limit - fetched_count)
                
                response = self.client.conversations_history(
                    channel=channel_id,
                    cursor=cursor,
                    limit=batch_limit
                )
                
                batch_messages = response['messages']
                if not batch_messages:
                    break
                
                for message in batch_messages:
                    # Skip bot messages and system messages
                    if message.get('bot_id') or message.get('subtype') in ['channel_join', 'channel_leave']:
                        continue
                    
                    # Get user display name
                    user_id = message.get('user', 'unknown')
                    user_name = self.get_user_info(user_id) if user_id != 'unknown' else 'unknown'
                    
                    message_data = {
                        "ts": message['ts'],
                        "text": message.get('text', ''),
                        "user_id": user_id,
                        "user_name": user_name,
                        "timestamp": datetime.fromtimestamp(float(message['ts']), tz=timezone.utc).isoformat(),
                        "type": message.get('type', 'message'),
                        "thread_ts": message.get('thread_ts'),
                        "reply_count": message.get('reply_count', 0),
                        "replies": []
                    }
                    
                    # Fetch thread replies if this is a parent message
                    if message.get('reply_count', 0) > 0:
                        replies = self.fetch_thread_replies(channel_id, message['ts'])
                        message_data['replies'] = replies
                    
                    messages.append(message_data)
                
                fetched_count += len(batch_messages)
                cursor = response.get('response_metadata', {}).get('next_cursor')
                
                if not cursor:
                    break
                
                print(f"  📝 Fetched {fetched_count} messages so far...")
            
            print(f"✅ Fetched {len(messages)} messages from channel {channel_id}")
            return messages
            
        except SlackApiError as e:
            raise Exception(f"Failed to fetch messages from channel {channel_id}: {e.response['error']}")
    
    def fetch_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Fetch replies in a thread"""
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=100
            )
            
            if not response or not response.get('messages'):
                return []
            
            replies = []
            # Skip the first message (it's the parent)
            messages_data = response.get('messages', [])
            if len(messages_data) > 1:
                for message in messages_data[1:]:
                    if message.get('bot_id') or message.get('subtype'):
                        continue
                    
                    user_id = message.get('user', 'unknown')
                    user_name = self.get_user_info(user_id) if user_id != 'unknown' else 'unknown'
                    
                    reply_data = {
                        "ts": message['ts'],
                        "text": message.get('text', ''),
                        "user_id": user_id,
                        "user_name": user_name,
                        "timestamp": datetime.fromtimestamp(float(message['ts']), tz=timezone.utc).isoformat(),
                        "parent_ts": thread_ts
                    }
                    replies.append(reply_data)
            
            return replies
            
        except SlackApiError as e:
            print(f"⚠️ Warning: Failed to fetch thread replies: {e.response['error']}")
            return []
    
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get information about a specific channel"""
        try:
            response = self.client.conversations_info(channel=channel_id)
            if not response or not response.get('channel'):
                raise Exception(f"Channel {channel_id} not found or inaccessible")
            
            channel = response.get('channel')
            if not channel:
                raise Exception(f"Channel {channel_id} data not found")
            
            return {
                "id": channel.get('id', channel_id),
                "name": channel.get('name', 'unknown'),
                "topic": (channel.get('topic') or {}).get('value', '') if channel.get('topic') else '',
                "purpose": (channel.get('purpose') or {}).get('value', '') if channel.get('purpose') else '',
                "member_count": channel.get('num_members', 0),
                "is_private": channel.get('is_private', False)
            }
        except SlackApiError as e:
            raise Exception(f"Failed to get channel info for {channel_id}: {e.response['error']}")
    
    def save_data(self, data: Dict[str, Any], filename: str) -> str:
        """Save data to JSON file in raw data directory"""
        os.makedirs(settings.RAW_DATA_PATH, exist_ok=True)
        filepath = os.path.join(settings.RAW_DATA_PATH, filename)
        
        # Add metadata
        data_with_metadata = {
            "metadata": {
                "fetched_at": datetime.now().isoformat(),
                "source": "slack",
                "user_cache_size": len(self.user_cache)
            },
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_with_metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved data to {filepath}")
        return filepath
    
    def fetch_workspace_data(self, channel_ids: Optional[List[str]] = None, 
                           messages_per_channel: int = 1000) -> Dict[str, str]:
        """Fetch data from specified channels or all accessible channels"""
        print("🚀 Starting Slack data fetch...")
        
        # Test connection
        self.test_connection()
        
        # Use provided channel IDs or get from settings
        if not channel_ids:
            channel_ids = settings.SLACK_CHANNELS
        
        if not channel_ids:
            print("📋 No specific channels configured, fetching available channels...")
            available_channels = self.get_channels()
            print(f"Found {len(available_channels)} accessible channels:")
            for channel in available_channels[:10]:  # Show first 10
                print(f"  - #{channel['name']} ({channel['id']})")
            
            # For demo purposes, use first few public channels
            channel_ids = [ch['id'] for ch in available_channels if not ch['is_private']][:3]
            print(f"📡 Will fetch from first 3 public channels: {channel_ids}")
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        for channel_id in channel_ids:
            try:
                # Get channel info
                channel_info = self.get_channel_info(channel_id)
                print(f"🔄 Processing channel: #{channel_info['name']} ({channel_id})")
                
                # Fetch messages
                messages = self.fetch_channel_messages(channel_id, messages_per_channel)
                
                # Prepare data for saving
                channel_data = {
                    "channel_info": channel_info,
                    "messages": messages,
                    "message_count": len(messages)
                }
                
                # Save to file
                filename = f"slack_channel_{channel_info['name']}_{timestamp}.json"
                filepath = self.save_data(channel_data, filename)
                saved_files[channel_info['name']] = filepath
                
            except Exception as e:
                print(f"❌ Error processing channel {channel_id}: {str(e)}")
                continue
        
        print(f"🎉 Completed Slack data fetch!")
        print(f"📈 Summary: {len(saved_files)} channels processed")
        
        return saved_files

def main():
    """Main function for testing the Slack connector"""
    try:
        connector = SlackConnector()
        
        # Test connection first
        connector.test_connection()
        
        # Get channel IDs from user input if not in settings
        channel_ids = settings.SLACK_CHANNELS
        if not channel_ids:
            print("\n💡 Tip: You can configure SLACK_CHANNELS in your .env file")
            channel_input = input("Enter Slack channel IDs (comma-separated, or press Enter to use accessible channels): ").strip()
            if channel_input:
                channel_ids = [ch.strip() for ch in channel_input.split(",")]
        
        # Fetch data
        files = connector.fetch_workspace_data(channel_ids)
        print(f"\n✅ Slack data ingestion complete!")
        print(f"📁 Files saved:")
        for channel_name, filepath in files.items():
            print(f"  - #{channel_name}: {filepath}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
