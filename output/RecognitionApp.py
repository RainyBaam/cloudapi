from flask import Flask, request, jsonify
import grpc
import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc

app = Flask(__name__)

def recognize_audio(audio_data):
   api_key = 'AQVNyLzYTpeHpwtCXjGJxYusuYqw4gPcLPwOCZMJ'
   cred = grpc.ssl_channel_credentials()
   channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
   stub = stt_service_pb2_grpc.RecognizerStub(channel)

   def gen():
      recognize_options = stt_pb2.StreamingOptions(
         recognition_model=stt_pb2.RecognitionModelOptions(
            audio_format=stt_pb2.AudioFormatOptions(
               raw_audio=stt_pb2.RawAudio(
                  audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                  sample_rate_hertz=8000,
                  audio_channel_count=1
               )
            ),
            text_normalization=stt_pb2.TextNormalizationOptions(
               text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
               profanity_filter=True,
               literature_text=False
            ),
            language_restriction=stt_pb2.LanguageRestrictionOptions(
               restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
               language_code=['ru-RU']
            ),
            audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME
         )
      )

      yield stt_pb2.StreamingRequest(session_options=recognize_options)

      for chunk in audio_data:
         yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=chunk))

   it = stub.RecognizeStreaming(gen(), metadata=(
      ('authorization', f'Api-Key {api_key}'),
   ))

   result = []
   for r in it:
      event_type, alternatives = r.WhichOneof('Event'), None
      if event_type == 'partial' and len(r.partial.alternatives) > 0:
         alternatives = [a.text for a in r.partial.alternatives]
      if event_type == 'final':
         alternatives = [a.text for a in r.final.alternatives]
      if event_type == 'final_refinement':
         alternatives = [a.text for a in r.final_refinement.normalized_text.alternatives]
      if alternatives:
         result.append({
            'type': event_type,
            'alternatives': alternatives
         })
   return result

@app.route('/recognize', methods=['POST'])
def recognize():
   audio_data = request.stream.read()
   audio_chunks = [audio_data[i:i+4096] for i in range(0, len(audio_data), 4096)]
   result = recognize_audio(audio_chunks)
   return jsonify(result)

if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0', port=5000)




