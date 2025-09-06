jq '
  def transform: { uri: .uri, metadata: { creation_timestamp: .creation_timestamp, title: .title } };
  if type == "array" then
    map(transform)
  elif type == "object" then
    ( .media? // .posts? // .ig_reels_media? // .items? // .data? // ( [ .[] | select(type=="array") ] | .[0] // [] ) )
    | map(transform)
  else
    []
  end
' "/Users/julian/Desktop/OMATA_IG_08202025/your_instagram_activity/media/prepared_stories.json" > ./test-output.json