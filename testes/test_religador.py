from nucleo import religador

YTDLP = r"C:\yt-dlp\yt-dlp.exe"
VELHA = "https://www.youtube.com/watch?v=VELHA123"
CANAL = "https://www.youtube.com/@amici1914"


def falso(respostas: dict):
    """Responde pelo que aparece no comando, para o teste nao depender de rede."""
    def rodar(comando):
        for chave, resposta in respostas.items():
            if any(chave in parte for parte in comando):
                return resposta
        return ""
    return rodar


def test_acha_a_live_nova_do_canal_quando_a_antiga_acabou():
    """Live encerrada nao volta: o canal abre outra, com outro endereco."""
    rodar = falso({"/live": "NOVA456|is_live", "VELHA123": CANAL})

    nova, canal = religador.procurar_substituta(VELHA, YTDLP, rodar=rodar)

    assert nova == "https://www.youtube.com/watch?v=NOVA456"
    assert canal == CANAL


def test_canal_sem_live_no_ar_nao_devolve_nada():
    rodar = falso({"/live": "ABC|post_live", "VELHA123": CANAL})

    assert religador.procurar_substituta(VELHA, YTDLP, rodar=rodar) == ("", CANAL)


def test_live_que_e_a_mesma_de_agora_nao_conta_como_nova():
    """Sem isto, um canal saudavel seria religado a toa a cada queda."""
    atual = "https://www.youtube.com/watch?v=IGUAL789"
    rodar = falso({"/live": "IGUAL789|is_live", "IGUAL789": CANAL})

    nova, canal = religador.procurar_substituta(atual, YTDLP, rodar=rodar)

    assert nova == "" and canal == CANAL


def test_endereco_do_canal_ja_conhecido_poupa_uma_ida_a_rede():
    chamadas = []

    def rodar(comando):
        chamadas.append(comando)
        return "NOVA456|is_live"

    religador.procurar_substituta(VELHA, YTDLP, url_canal=CANAL, rodar=rodar)

    assert len(chamadas) == 1, "com o canal em cache, so a pergunta da live"


def test_yt_dlp_mudo_ou_com_erro_nao_derruba_nada():
    for resposta in ("", "ERROR: unable to download", "NA"):
        assert religador.procurar_substituta(
            VELHA, YTDLP, rodar=lambda c, r=resposta: r
        ) == ("", "")


def test_saida_com_aviso_antes_ainda_e_lida():
    """O yt-dlp as vezes cospe linha de aviso antes do que foi pedido."""
    rodar = falso({"/live": "\nWARNING: algo\nNOVA456|is_live\n", "VELHA123": f"\n{CANAL}\n"})

    nova, _ = religador.procurar_substituta(VELHA, YTDLP, rodar=rodar)

    assert nova == "https://www.youtube.com/watch?v=NOVA456"
