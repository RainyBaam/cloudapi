# -*- coding: cp1251 -*-
import pyaudio
import wave
import grpc
import os
import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc

# Настройки потокового распознавания.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 4096
RECORD_SECONDS = 15
WAVE_OUTPUT_FILENAME = "audio.wav"
TEXT_OUTPUT_FILENAME = os.path.join(os.path.dirname(__file__),'recognized_text.txt')

audio = pyaudio.PyAudio()

def gen():
   # Задайте настройки распознавания.
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

   # Отправьте сообщение с настройками распознавания.
   yield stt_pb2.StreamingRequest(session_options=recognize_options)

   # Начните запись голоса.
   stream = audio.open(format=FORMAT, channels=CHANNELS,
               rate=RATE, input=True,
               frames_per_buffer=CHUNK)
   print("recording")
   frames = []

   # Распознайте речь по порциям.
   for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
      data = stream.read(CHUNK)
      yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
      frames.append(data)
   print("finished")

   # Остановите запись.
   stream.stop_stream()
   stream.close()
   audio.terminate()

   # Создайте файл WAV с записанным голосом.
   waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
   waveFile.setnchannels(CHANNELS)
   waveFile.setsampwidth(audio.get_sample_size(FORMAT))
   waveFile.setframerate(RATE)
   waveFile.writeframes(b''.join(frames))
   waveFile.close()

def run():
   # Установите соединение с сервером.
   api_key = 'AQVNyLzYTpeHpwtCXjGJxYusuYqw4gPcLPwOCZMJ'
   cred = grpc.ssl_channel_credentials()
   channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
   stub = stt_service_pb2_grpc.RecognizerStub(channel)

   # Отправьте данные для распознавания.
   it = stub.RecognizeStreaming(gen(), metadata=(
   # Параметры для аутентификации с API-ключом от имени сервисного аккаунта
      ('authorization', f'Api-Key {api_key}'),
   # Для аутентификации с IAM-токеном используйте строку ниже
   #   ('authorization', f'Bearer {secret}'),
   ))

   # Обработайте ответы сервера и запишите результат в файл.
   final_alternatives = set()

   unique_sentences = set()

   with open(TEXT_OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        try:
            for r in it:
                if r.WhichOneof('Event') == 'final':
                    alternatives = [a.text for a in r.final.alternatives]
                    for alternative in alternatives:
                        if alternative not in unique_sentences:
                            unique_sentences.add(alternative)
                            f.write(f'{alternative}\n')
                            print(alternative)
                    
        except grpc._channel._Rendezvous as err:
            print(f'Error code {err._state.code}, message: {err._state.details}')
            raise err

if __name__ == '__main__':
   run()