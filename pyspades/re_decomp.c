/*
    Copyright (c) Mathias Kaerlev 2011.

    This file is part of pyspades.

    pyspades is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pyspades is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyspades.  If not, see <http://www.gnu.org/licenses/>.
*/

#include <stdio.h>

#define _DWORD unsigned int
#define DWORD unsigned int
#define _WORD unsigned short
#define _BYTE unsigned char
#define __int8 char
#define __int16 short
#define __int64 long long
#define DWORDLONG long long

#define LODWORD(l) ((DWORD)((DWORDLONG)(l)))
#define HIDWORD(l) ((DWORD)(((DWORDLONG)(l)>>32)&0xFFFFFFFF))

struct struct_code_tables
{
  char byte_value;
  unsigned __int8 field_1;
  __int16 field_2;
  __int16 skip_entries1;
  __int16 skip_entries2;
  _WORD next_index;
  unsigned __int16 dwordA;
  unsigned __int16 code_no;
  _WORD prev_index;
};

__int16 __cdecl do_codeentry_stuff(struct_code_tables * code_entry)
{
  __int16 v1; // di@1
  struct_code_tables *v2; // esi@1
  int v3; // eax@2
  unsigned __int8 v4; // al@2
  __int16 v5; // dx@2
  int v6; // eax@4

  v2 = code_entry;
  v1 = 0;
  while ( 1 )
  {
    v4 = v2->field_1 - (v2->field_1 >> 1);
    v5 = v4;
    v2->field_1 = v4;
    v3 = v2->skip_entries1;
    v2->field_2 = v5;
    if ( (_WORD)v3 )
      v2->field_2 += do_codeentry_stuff(&v2[v3]);
    v6 = v2->skip_entries2;
    v1 += v2->field_2;
    if ( !(_WORD)v6 )
      break;
    v2 += v6;
  }
  return v1;
}

unsigned int decompress_1(struct_code_tables * code_tables, unsigned char * in_data, 
    unsigned int in_size, unsigned char *out_data, int out_size)
{
  unsigned char * in_end; // edx@1
  int v6; // edi@1
  unsigned int v7; // esi@1
  unsigned __int8 *v8; // eax@4
  int v9; // ecx@4
  unsigned __int8 *v10; // eax@5
  int v11; // ecx@5
  int v12; // esi@5
  unsigned char * v13; // eax@6
  int v14; // ecx@6
  int v15; // esi@6
  struct_code_tables *v16; // eax@8
  struct_code_tables *v17; // ebx@8
  int v18; // esi@8
  int v19; // ecx@9
  unsigned int v20; // eax@10
  unsigned __int16 v21; // bx@11
  int v22; // ebp@11
  __int64 v23; // qax@11
  unsigned __int64 v24; // qtt@11
  unsigned __int8 *v25; // eax@12
  int v26; // eax@21
  unsigned int v27; // ecx@21
  int v28; // eax@22
  struct_code_tables *v29; // eax@23
  unsigned __int8 v30; // bl@23
  unsigned __int16 v31; // di@23
  struct_code_tables *v32; // edx@23
  int v33; // eax@24
  intptr_t v34; // ecx@24
  unsigned __int16 v35; // bx@24
  intptr_t v36; // eax@25
  int v37; // edx@27
  int v38; // ecx@27
  int v39; // edi@27
  int v40; // esi@27
  int v41; // edx@28
  int v42; // ecx@28
  int v43; // ecx@31
  int v44; // eax@33
  unsigned __int16 v45; // dx@33
  unsigned __int8 v46; // cl@33
  unsigned __int8 *v47; // ecx@33
  struct_code_tables *v48; // esi@33
  int v49; // edi@33
  int v50; // eax@43
  __int16 v51; // cx@44
  unsigned __int16 v52; // ax@46
  intptr_t i; // ecx@47
  int v54; // eax@48
  unsigned __int16 v55; // dx@48
  int v56; // edi@48
  int v57; // edx@49
  int v58; // edi@52
  signed int v59; // edx@54
  char v60; // bl@54
  char v61; // bl@55
  signed int v62; // edx@55
  unsigned __int8 v63; // dl@56
  int v64; // eax@56
  int v65; // eax@57
  int v66; // edx@57
  unsigned __int8 *v67; // ecx@57
  unsigned __int16 v68; // cx@64
  int v69; // eax@66
  __int16 v70; // cx@67
  unsigned __int16 v71; // ax@69
  struct_code_tables *v72; // esi@70
  struct_code_tables *v73; // ebp@71
  int v74; // eax@72
  struct_code_tables *v75; // eax@73
  signed int v76; // edx@73
  intptr_t j; // ecx@74
  int v78; // eax@76
  int v79; // eax@79
  signed int v80; // edx@81
  signed int v81; // edx@82
  unsigned __int8 v82; // al@83
  int * v83; // edx@84
  int v84; // eax@88
  __int16 v85; // cx@89
  unsigned __int16 v86; // ax@91
  int v87; // eax@99
  unsigned __int8 *v88; // ecx@99
  signed int v90; // [sp+Ch] [bp-38h]@3
  int v91; // [sp+10h] [bp-34h]@1
  int v92; // [sp+10h] [bp-34h]@24
  struct_code_tables *v93; // [sp+14h] [bp-30h]@8
  int v94; // [sp+18h] [bp-2Ch]@22
  int v95; // [sp+18h] [bp-2Ch]@24
  signed __int16 v96; // [sp+1Ch] [bp-28h]@22
  unsigned __int16 v97; // [sp+1Ch] [bp-28h]@72
  int v98; // [sp+20h] [bp-24h]@1
  unsigned int v99; // [sp+24h] [bp-20h]@1
  unsigned char * in_end2; // [sp+28h] [bp-1Ch]@1
  int * v101; // [sp+2Ch] [bp-18h]@8
  int v102; // [sp+30h] [bp-14h]@48
  unsigned int v103; // [sp+34h] [bp-10h]@21
  struct_code_tables *v104; // [sp+38h] [bp-Ch]@8
  unsigned char * out_end; // [sp+3Ch] [bp-8h]@1
  unsigned __int8 *v106; // [sp+40h] [bp-4h]@1
  int v107; // [sp+50h] [bp+Ch]@1
  unsigned int v108; // [sp+58h] [bp+14h]@21
  int v109; // [sp+58h] [bp+14h]@22
  unsigned __int16 v110; // [sp+58h] [bp+14h]@24
  int v111; // [sp+58h] [bp+14h]@33

  v106 = out_data;
  v7 = in_size;
  out_end = &out_data[out_size];
  in_end = &in_data[in_size];
  v6 = -1;
  in_end2 = &in_data[in_size];
  v91 = 0;
  v107 = 0;
  v98 = 0;
  v99 = 0;
  if ( !code_tables || v7 <= 0 )
    return 0;
  code_tables->skip_entries1 = 0;
  code_tables->skip_entries2 = 0;
  code_tables->prev_index = 0;
  code_tables->dwordA = 1;
  code_tables->code_no = 257;
  v90 = 1;
  *(_DWORD *)&code_tables->byte_value = 0;
  code_tables->next_index = 0;
  if (in_data < in_end)
  {
    v8 = in_data + 1;
    v9 = *in_data << 24;
    v107 = *in_data << 24;
    in_data = v8;
    if (v8 < in_end )
    {
      v12 = *v8 << 16;
      v10 = v8 + 1;
      v11 = v12 | v9;
      v107 = v11;
      in_data = v10;
      if (v10 < in_end )
      {
        v15 = *v10 << 8;
        v13 = v10 + 1;
        v14 = v15 | v11;
        v107 = v14;
        in_data = v13;
        if ( v13 < in_end )
        {
          v107 = *v13 | v14;
          in_data = (unsigned __int8 *)(v13 + 1);
        }
      }
    }
  }
  while ( 2 )
  {
    v17 = code_tables;
    v18 = v91;
    v101 = &v98;
    v16 = &code_tables[(unsigned __int16)v98];
    v104 = v16;
    v93 = &code_tables[(unsigned __int16)v98];
    if ( v16 == code_tables )
    {
LABEL_21:
      
      v27 = v6 / (unsigned int)v17->code_no;
      v103 = v27;
      v26 = v17->dwordA;
      v108 = (v107 - v18) / v27;
      if ( (_WORD)v108 >= (_WORD)v26 )
      {
        v109 = v108 - v26;
        v28 = v17->next_index;
        v94 = 0;
        v96 = 1;
        if ( (_WORD)v28 )
        {
          for ( i = (intptr_t)&v17[v28]; ; i += 16 * v57 )
          {
            while ( 1 )
            {
              v56 = *(_WORD *)(i + 2);
              v54 = (unsigned __int16)((_WORD)v94 + v56 + *(_BYTE *)i + 1);
              v55 = *(_BYTE *)(i + 1) + 1;
              v102 = (unsigned __int16)(*(_BYTE *)(i + 1) + 1);
              if ( (_WORD)v109 >= (_WORD)v54 )
                break;
              if ( (unsigned __int16)v109 >= v54 - v55 )
              {
                v63 = *(_BYTE *)(i + 1);
                v64 = v54 - v102;
                *(_WORD *)(i + 2) += 3;
                v30 = *(_BYTE *)i;
                v31 = v64;
                *(_BYTE *)(i + 1) += 3;
                v96 = v63 + 1;
                v29 = (struct_code_tables *)i;
                goto LABEL_57;
              }
              *(_WORD *)(i + 2) = v56 + 3;
              v58 = *(_WORD *)(i + 4);
              if ( !(_WORD)v58 )
              {
                v61 = v55 + *(_BYTE *)i - v54;
                v62 = v90;
                v30 = v109 + v61;
                ++v90;
                v29 = &code_tables[v62];
                v29->field_2 = 3;
                v29->skip_entries1 = 0;
                v29->skip_entries2 = 0;
                v29->next_index = 0;
                v29->dwordA = 0;
                v29->code_no = 0;
                v29->prev_index = 0;
                v29->byte_value = v30;
                v29->field_1 = 3;
                v31 = v109;
                *(_WORD *)(i + 4) = (intptr_t)((char *)v29 - i) >> 4;
                goto LABEL_57;
              }
              i += 16 * v58;
            }
            v57 = *(_WORD *)(i + 6);
            v94 += v56;
            if ( !(_WORD)v57 )
              break;
          }
          v59 = v90;
          v60 = v109 + *(_BYTE *)i - v54;
          ++v90;
          v29 = &code_tables[v59];
          v29->field_2 = 3;
          v29->skip_entries1 = 0;
          v29->skip_entries2 = 0;
          v29->next_index = 0;
          v29->dwordA = 0;
          v29->code_no = 0;
          v29->prev_index = 0;
          v30 = v60 + 1;
          v29->byte_value = v30;
          v29->field_1 = 3;
          v31 = v109;
          *(_WORD *)(i + 6) = (intptr_t)((char *)v29 - i) >> 4;
        }
        else
        {
          v30 = v109;
          v31 = v109;
          v29 = &code_tables[v90];
          v32 = &code_tables[v90++];
          v29->byte_value = v109;
          v29->field_1 = 3;
          *(_DWORD *)&v29->field_2 = 3;
          *(_DWORD *)&v29->skip_entries2 = 0;
          *(_DWORD *)&v29->dwordA = 0;
          v29->prev_index = 0;
          code_tables->next_index = (signed int)((char *)v32 - (char *)code_tables) >> 4;
        }
LABEL_57:
        v111 = (unsigned __int16)((signed int)((char *)v29 - (char *)code_tables) >> 4);
        v65 = v103 * (v31 + code_tables->dwordA) + v91;
        v6 = v103 * (unsigned __int16)v96;
        v67 = in_data;
        v66 = v107;
        while ( 1 )
        {
          if ( (v65 ^ (unsigned int)(v6 + v65)) >= 0x1000000 )
          {
            if ( (unsigned int)v6 >= 0x10000 )
            {
              v91 = v65;
              v107 = v66;
              in_data = v67;
              v68 = code_tables->code_no + 3;
              code_tables->code_no = v68;
              if ( (unsigned __int16)v96 > 0xFAu || v68 > 0xFF00u )
              {
                v69 = code_tables->next_index;
                if ( (_WORD)v69 )
                  v70 = do_codeentry_stuff(&code_tables[v69]);
                else
                  v70 = 0;
                v71 = code_tables->dwordA - (code_tables->dwordA >> 1);
                code_tables->dwordA = v71;
                code_tables->code_no = v71 + v70 + 256;
              }
              goto LABEL_70;
            }
            v6 = -v65 & 0xFFFF;
          }
          v66 <<= 8;
          if (v67 < in_end2)
            v66 |= *v67++;
          v6 <<= 8;
          v65 <<= 8;
        }
      }
      v87 = v27 * v17->dwordA;
      v88 = in_data;
      while ( 1 )
      {
        if ( (v18 ^ (unsigned int)(v87 + v18)) >= 0x1000000 )
        {
          if ( (unsigned int)v87 >= 0x10000 )
            return out_data - v106;
          v87 = -v18 & 0xFFFF;
        }
        if (v88 < in_end2 )
          ++v88;
        v87 <<= 8;
        v18 <<= 8;
      }
    }
    while ( 1 )
    {
      v19 = v16->dwordA;
      if ( (_WORD)v19 )
      {
        v20 = v16->code_no;
        if ( (_WORD)v19 < (_WORD)v20 )
          break;
      }
LABEL_19:
      v17 = code_tables;
      v16 = &code_tables[v93->prev_index];
      v93 = v16;
      if ( v16 == code_tables )
      {
        v91 = v18;
        goto LABEL_21;
      }
    }
    v23 = v6 / v20;
    v22 = v23;
    v24 = ((v107 - v18) & 0xFFFFFFFF) | (HIDWORD(v23) << 32);
    v21 = v24 / (unsigned int)v23;
    if ( v21 < (_WORD)v19 )
    {
      v25 = in_data;
      v6 = v22 * v19;
      while ( 1 )
      {
        if ( (v18 ^ (unsigned int)(v6 + v18)) >= (unsigned int)0x1000000 )
        {
          if ( (unsigned int)v6 >= 0x10000 )
            goto LABEL_19;
          v25 = in_data;
          v6 = -v18 & 0xFFFF;
        }
        v107 <<= 8;
        if (v25 < in_end2 )
        {
          v107 |= *v25++;
          in_data = v25;
        }
        v6 <<= 8;
        v18 <<= 8;
      }
    }
    v34 = (intptr_t)v93;
    v33 = v93->next_index;
    v35 = v21 - v93->dwordA;
    v92 = v18;
    v110 = v35;
    v95 = 0;
    if ( !(_WORD)v33 )
      return 0;
    v36 = 16 * v33;
LABEL_26:
    for ( v36 += v34; ; v36 += 16 * v43 )
    {
      v37 = *(_WORD *)(v36 + 2);
      v40 = *(_BYTE *)(v36 + 1);
      v38 = v37 + v95;
      v39 = (unsigned __int16)(v37 + (_WORD)v95);
      if ( v35 >= (_WORD)v39 )
      {
        v41 = (unsigned __int16)v38;
        v42 = *(_WORD *)(v36 + 6);
        v95 = v41;
        if ( !(_WORD)v42 )
          return 0;
        v34 = 16 * v42;
        goto LABEL_26;
      }
      if ( v110 >= v39 - v40 )
        break;
      v43 = *(_WORD *)(v36 + 4);
      *(_WORD *)(v36 + 2) = v37 + 2;
      if ( !(_WORD)v43 )
        return 0;
      v35 = v110;
    }
    v46 = *(_BYTE *)(v36 + 1);
    *(_WORD *)(v36 + 2) += 2;
    v30 = *(_BYTE *)v36;
    v45 = v46;
    *(_BYTE *)(v36 + 1) = v46 + 2;
    v49 = v39 - v40;
    v48 = v93;
    v111 = (unsigned __int16)((v36 - (uintptr_t)code_tables) >> 4);
    v44 = v22 * (v93->dwordA + (unsigned __int16)v49) + v92;
    v6 = v22 * v46;
    v47 = in_data;
    while ( 1 )
    {
      if ( (v44 ^ (unsigned int)(v6 + v44)) < (unsigned int)0x1000000 )
        goto LABEL_37;
      if ( (unsigned int)v6 >= 0x10000 )
        break;
      v6 = -v44 & 0xFFFF;
LABEL_37:
      v107 <<= 8;
      if (v47 < in_end2)
      {
        v107 |= *v47;
        v48 = v93;
        ++v47;
      }
      v6 <<= 8;
      v44 <<= 8;
    }
    v48->code_no += 2;
    in_data = v47;
    v91 = v44;
    if ( v45 <= 0xFBu )
    {
      if ( v48->code_no <= 0xFF00u )
        goto LABEL_70;
      v48 = v93;
    }
    v50 = v48->next_index;
    if ( (_WORD)v50 )
      v51 = do_codeentry_stuff(&v93[v50]);
    else
      v51 = 0;
    v52 = v93->dwordA - (v93->dwordA >> 1);
    v93->dwordA = v52;
    v93->code_no = v52 + v51;
LABEL_70:
    v72 = v104;
    if ( v104 != v93 )
    {
      v73 = &code_tables[v90];
      do
      {
        v74 = v72->next_index;
        v97 = 0;
        if ( (_WORD)v74 )
        {
          for ( j = (intptr_t)&v72[v74]; ; j += 16 * v79 )
          {
            while ( v30 < *(_BYTE *)j )
            {
              v78 = *(_WORD *)(j + 4);
              *(_WORD *)(j + 2) += 2;
              if ( !(_WORD)v78 )
              {
                ++v90;
                v75 = v73;
                v73->field_1 = 2;
                v73->field_2 = 2;
                v73->skip_entries1 = 0;
                v73->skip_entries2 = 0;
                v73->next_index = 0;
                v73->dwordA = 0;
                v73->code_no = 0;
                v73->prev_index = 0;
                v80 = (intptr_t)((char *)v73 - j);
                ++v73;
                v75->byte_value = v30;
                *(_WORD *)(j + 4) = v80 >> 4;
                goto LABEL_84;
              }
              j += 16 * v78;
            }
            if ( v30 <= *(_BYTE *)j )
              break;
            v79 = *(_WORD *)(j + 6);
            if ( !(_WORD)v79 )
            {
              ++v90;
              v75 = v73;
              v73->field_1 = 2;
              v73->field_2 = 2;
              v73->skip_entries1 = 0;
              v73->skip_entries2 = 0;
              v73->next_index = 0;
              v73->dwordA = 0;
              v73->code_no = 0;
              v73->prev_index = 0;
              v81 = (intptr_t)((char *)v73 - j);
              ++v73;
              v75->byte_value = v30;
              *(_WORD *)(j + 6) = v81 >> 4;
              goto LABEL_84;
            }
          }
          v82 = *(_BYTE *)(j + 1);
          *(_WORD *)(j + 2) += 2;
          *(_BYTE *)(j + 1) = v82 + 2;
          v97 = v82;
          v75 = (struct_code_tables *)j;
        }
        else
        {
          ++v90;
          v75 = v73;
          v76 = (char *)v73 - (char *)v72;
          ++v73;
          v75->byte_value = v30;
          v75->field_1 = 2;
          *(_DWORD *)&v75->field_2 = 2;
          *(_DWORD *)&v75->skip_entries2 = 0;
          *(_DWORD *)&v75->dwordA = 0;
          v75->prev_index = 0;
          v72->next_index = v76 >> 4;
        }
LABEL_84:
        v83 = v101;
        v101 = (int*)(&v75->prev_index);
        *(_WORD *)v83 = (signed int)((char *)v75 - (char *)code_tables) >> 4;
        if ( !v97 )
        {
          v72->dwordA += 5;
          v72->code_no += 5;
        }
        v72->code_no += 2;
        if ( v97 > 0xFBu || v72->code_no > 0xFF00u )
        {
          v84 = v72->next_index;
          if ( (_WORD)v84 )
            v85 = do_codeentry_stuff(&v72[v84]);
          else
            v85 = 0;
          v86 = v72->dwordA - (v72->dwordA >> 1);
          v72->dwordA = v86;
          v72->code_no = v86 + v85;
        }
        v72 = &code_tables[v72->prev_index];
      }
      while ( v72 != v93 );
    }
    *(_WORD *)v101 = v111;
    if (out_data < out_end )
    {
      *out_data++ = v30;
      if ( v99 < 2 )
        ++v99;
      else
        v98 = code_tables[(unsigned __int16)v98].prev_index;
      if ( (unsigned int)v90 >= 0xFFE )
      {
        *(_DWORD *)&code_tables->byte_value = 0;
        *(_DWORD *)&code_tables->skip_entries1 = 0;
        code_tables->prev_index = 0;
        *(_DWORD *)&code_tables->dwordA = 0x1010001u;
        code_tables->next_index = 0;
        v90 = 1;
        v98 = 0;
        v99 = 0;
      }
      continue;
    }
    return 0;
  }
}

struct struct_in_data
{
  _DWORD block_size;
  char *data;
};

unsigned int __cdecl compress_1(struct_code_tables *output_table, struct_in_data *in_data, unsigned int block_count, unsigned int total_size, char *out_data, int total_block_size)
{
  char *out_data3; // eax@1
  unsigned int v7; // ebx@1
  intptr_t output_table2; // ebp@1
  unsigned int v9; // edi@1
  intptr_t v10; // ecx@4
  char *v11; // esi@4
  char *v12; // eax@8
  char v13; // dl@9
  intptr_t v14; // esi@9
  intptr_t v15; // ecx@10
  int v16; // eax@12
  intptr_t v17; // eax@13
  intptr_t k; // ecx@14
  int v19; // eax@16
  int v20; // eax@19
  unsigned __int8 v21; // al@23
  int v22; // ebp@23
  unsigned int v23; // eax@24
  unsigned __int16 v24; // cx@24
  unsigned int v25; // eax@25
  int v26; // ecx@31
  int v27; // eax@42
  int v28; // ecx@43
  int v29; // eax@45
  int v30; // eax@45
  int v31; // eax@48
  intptr_t v32; // eax@49
  signed int v33; // eax@49
  intptr_t i; // ecx@50
  unsigned __int16 v35; // si@50
  int v36; // eax@52
  int v37; // eax@55
  unsigned __int8 v38; // al@59
  int v39; // esi@59
  unsigned int v40; // eax@60
  unsigned __int16 v41; // cx@66
  int v42; // eax@68
  __int16 v43; // cx@69
  unsigned __int16 v44; // ax@71
  char *v45; // esi@78
  signed int v47; // [sp+Ch] [bp-30h]@4
  unsigned int v48; // [sp+10h] [bp-2Ch]@12
  unsigned int v49; // [sp+10h] [bp-2Ch]@48
  intptr_t j; // [sp+14h] [bp-28h]@10
  unsigned __int16 v51; // [sp+18h] [bp-24h]@12
  unsigned __int16 v52; // [sp+18h] [bp-24h]@48
  unsigned int v53; // [sp+1Ch] [bp-20h]@1
  int v54; // [sp+20h] [bp-1Ch]@1
  char *v55; // [sp+24h] [bp-18h]@4
  unsigned int v56; // [sp+28h] [bp-14h]@1
  char *v57; // [sp+2Ch] [bp-10h]@1
  int *v58; // [sp+30h] [bp-Ch]@6
  char *v59; // [sp+34h] [bp-8h]@4
  char *out_data2; // [sp+38h] [bp-4h]@1
  intptr_t v61; // [sp+44h] [bp+8h]@4
  unsigned int v62; // [sp+48h] [bp+Ch]@4
  char v63; // [sp+54h] [bp+18h]@9

  out_data3 = out_data;
  output_table2 = (intptr_t)output_table;
  v7 = 0;
  v9 = -1;
  out_data2 = out_data;
  v57 = &out_data[total_block_size];
  v53 = 0;
  v54 = 0;
  v56 = 0;
  if ( output_table && block_count > 0 && total_size > 0 )
  {
    v11 = in_data->data;
    v59 = &v11[in_data->block_size];
    v62 = block_count - 1;
    v55 = v11;
    v10 = (intptr_t)(&in_data[1].block_size);
    v47 = 1;
    output_table->dwordA = 1;
    v61 = (intptr_t)(&in_data[1].block_size);
    *(_DWORD *)&output_table->byte_value = 0;
    output_table->skip_entries1 = 0;
    output_table->skip_entries2 = 0;
    *(_DWORD *)&output_table->code_no = 257;
    output_table->next_index = 0;
LABEL_6:
    v58 = &v54;
    if ( v55 >= v59 )
    {
      if ( !v62 )
      {
        if ( !v7 )
          return out_data3 - out_data2;
        v45 = v57;
        while ( out_data3 < v45 )
        {
          *out_data3 = v7 >> 24;
          v7 <<= 8;
          ++out_data3;
          if ( !v7 )
            return out_data3 - out_data2;
        }
        return 0;
      }
      v12 = (char *)(*(_DWORD *)(v10 + 4) + *(_DWORD *)v10);
      --v62;
      v55 = *(char **)(v10 + 4);
      v59 = v12;
      v61 = v10 + 8;
    }
    v13 = *v55;
    v14 = (intptr_t)(output_table2 + 16 * (unsigned __int16)v54);
    v63 = *v55++;
    if ( v14 == output_table2 )
    {
LABEL_48:
      v31 = *(_WORD *)(output_table2 + 8);
      *(_DWORD *)&v49 = (unsigned __int8)v13;
      v52 = 1;
      if ( (_WORD)v31 )
      {
        v35 = v49;
        for ( i = (intptr_t)(output_table2 + 16 * v31); ; i += 16 * v36 )
        {
          while ( (unsigned __int8)v13 >= *(_BYTE *)i )
          {
            if ( (unsigned __int8)v13 <= *(_BYTE *)i )
            {
              v38 = *(_BYTE *)(i + 1);
              v52 = v38 + 1;
              *(_DWORD *)&v49 += *(_WORD *)(i + 2) - v38;
              v7 = v53;
              v39 = *(_WORD *)(i + 2) + 3;
              *(_BYTE *)(i + 1) = v38 + 3;
              *(_WORD *)(i + 2) = v39;
              v32 = i;
              goto LABEL_60;
            }
            v37 = *(_WORD *)(i + 6);
            v35 += *(_WORD *)(i + 2);
            v49 = v35;
            if ( !(_WORD)v37 )
            {
              v32 = (intptr_t)(output_table2 + 16 * v47);
              *(_BYTE *)v32 = v13;
              *(_WORD *)(output_table2 + 2 + 16 * v47) = 3;
              *(_WORD *)(output_table2 + 4 + 16 * v47) = 0;
              *(_WORD *)(output_table2 + 6 + 16 * v47) = 0;
              *(_WORD *)(output_table2 + 8 + 16 * v47) = 0;
              *(_WORD *)(output_table2 + 10 + 16 * v47) = 0;
              *(_WORD *)(output_table2 + 12 + 16 * v47) = 0;
              *(_WORD *)(output_table2 + 14 + 16 * v47) = 0;
              *(_BYTE *)(output_table2 + 1 + 16 * v47++) = 3;
              *(_WORD *)(i + 6) = (v32 - i) >> 4;
              goto LABEL_60;
            }
            i += 16 * v37;
          }
          v36 = *(_WORD *)(i + 4);
          *(_WORD *)(i + 2) += 3;
          if ( !(_WORD)v36 )
            break;
        }
        v32 = (intptr_t)(output_table2 + 16 * v47);
        *(_BYTE *)v32 = v13;
        *(_WORD *)(output_table2 + 2 + 16 * v47) = 3;
        *(_WORD *)(output_table2 + 4 + 16 * v47) = 0;
        *(_WORD *)(output_table2 + 6 + 16 * v47) = 0;
        *(_WORD *)(output_table2 + 8 + 16 * v47) = 0;
        *(_WORD *)(output_table2 + 10 + 16 * v47) = 0;
        *(_WORD *)(output_table2 + 12 + 16 * v47) = 0;
        *(_WORD *)(output_table2 + 14 + 16 * v47) = 0;
        *(_BYTE *)(output_table2 + 1 + 16 * v47++) = 3;
        *(_WORD *)(i + 4) = (v32 - i) >> 4;
      }
      else
      {
        v33 = v47++;
        v32 = (intptr_t)(output_table2 + 16 * v33);
        *(_BYTE *)v32 = v13;
        *(_BYTE *)(v32 + 1) = 3;
        *(_DWORD *)(v32 + 2) = 3;
        *(_DWORD *)(v32 + 6) = 0;
        *(_DWORD *)(v32 + 10) = 0;
        *(_WORD *)(v32 + 14) = 0;
        *(_WORD *)(output_table2 + 8) = (v32 - output_table2) >> 4;
      }
LABEL_60:
      *(_WORD *)v58 = (v32 - output_table2) >> 4;
      v40 = v9 / *(_WORD *)(output_table2 + 12);
      v7 += v40 * (v49 + *(_WORD *)(output_table2 + 10));
      v9 = v40 * v52;
      while ( 1 )
      {
        v53 = v7;
        if ( (v7 ^ (v9 + v7)) >= 0x1000000 )
        {
          if ( v9 >= 0x10000 )
          {
            v41 = *(_WORD *)(output_table2 + 12) + 3;
            *(_WORD *)(output_table2 + 12) = v41;
            if ( v52 > 0xFAu || v41 > 0xFF00u )
            {
              v42 = *(_WORD *)(output_table2 + 8);
              if ( (_WORD)v42 )
                v43 = do_codeentry_stuff((struct_code_tables *)(output_table2 + 16 * v42));
              else
                v43 = 0;
              v44 = *(_WORD *)(output_table2 + 10) - (*(_WORD *)(output_table2 + 10) >> 1);
              *(_WORD *)(output_table2 + 10) = v44;
              *(_WORD *)(output_table2 + 12) = v43 + v44 + 256;
            }
            goto LABEL_72;
          }
          v9 = -v7 & 0xFFFF;
        }
        if ( out_data >= v57 )
          return 0;
        *out_data = v7 >> 24;
        v9 <<= 8;
        ++out_data;
        v7 <<= 8;
      }
    }
    v15 = (intptr_t)(output_table2 + 16 * v47);
    for ( j = (intptr_t)(output_table2 + 16 * v47); ; v15 = j )
    {
      v48 = 0;
      v51 = 0;
      v16 = *(_WORD *)(v14 + 8);
      if ( (_WORD)v16 )
      {
        for ( k = (intptr_t)(v14 + 16 * v16); ; k += 16 * v20 )
        {
          while ( (unsigned __int8)v13 < *(_BYTE *)k )
          {
            v19 = *(_WORD *)(k + 4);
            *(_WORD *)(k + 2) += 2;
            if ( !(_WORD)v19 )
            {
              v17 = j;
              ++v47;
              j += 16;
              *(_BYTE *)v17 = v63;
              *(_WORD *)(v17 + 2) = 2;
              *(_WORD *)(v17 + 4) = 0;
              *(_WORD *)(v17 + 6) = 0;
              *(_WORD *)(v17 + 8) = 0;
              *(_WORD *)(v17 + 10) = 0;
              *(_WORD *)(v17 + 12) = 0;
              *(_WORD *)(v17 + 14) = 0;
              *(_BYTE *)(v17 + 1) = 2;
              *(_WORD *)(k + 4) = (v17 - k) >> 4;
              goto LABEL_24;
            }
            k += 16 * v19;
          }
          if ( (unsigned __int8)v13 <= *(_BYTE *)k )
            break;
          v48 += *(_WORD *)(k + 2);
          v20 = *(_WORD *)(k + 6);
          if ( !(_WORD)v20 )
          {
            v17 = j;
            ++v47;
            j += 16;
            *(_BYTE *)v17 = v63;
            *(_WORD *)(v17 + 2) = 2;
            *(_WORD *)(v17 + 4) = 0;
            *(_WORD *)(v17 + 6) = 0;
            *(_WORD *)(v17 + 8) = 0;
            *(_WORD *)(v17 + 10) = 0;
            *(_WORD *)(v17 + 12) = 0;
            *(_WORD *)(v17 + 14) = 0;
            *(_BYTE *)(v17 + 1) = 2;
            *(_WORD *)(k + 6) = (v17 - k) >> 4;
            goto LABEL_24;
          }
        }
        v21 = *(_BYTE *)(k + 1);
        v22 = *(_WORD *)(k + 2);
        v51 = v21;
        v48 += v22 - v21;
        v7 = v53;
        *(_WORD *)(k + 2) = v22 + 2;
        output_table2 = (intptr_t)output_table;
        *(_BYTE *)(k + 1) = v21 + 2;
        v17 = k;
      }
      else
      {
        ++v47;
        j += 16;
        v17 = v15;
        *(_BYTE *)v15 = v13;
        *(_BYTE *)(v15 + 1) = 2;
        *(_DWORD *)(v15 + 2) = 2;
        *(_DWORD *)(v15 + 6) = 0;
        *(_DWORD *)(v15 + 10) = 0;
        *(_WORD *)(v15 + 14) = 0;
        *(_WORD *)(v14 + 8) = (v15 - v14) >> 4;
      }
LABEL_24:
      *(_WORD *)v58 = (v17 - output_table2) >> 4;
      v24 = v51;
      v58 = (int *)(v17 + 14);
      v23 = *(_WORD *)(v14 + 12);
      if ( v51 )
      {
        v25 = v9 / v23;
        v7 += v25 * (v48 + *(_WORD *)(v14 + 10));
        v9 = v25 * v51;
        while ( 1 )
        {
          v53 = v7;
          if ( (v7 ^ (v9 + v7)) >= 0x1000000 )
          {
            if ( v9 >= 0x10000 )
              goto LABEL_40;
            v9 = -v7 & 0xFFFF;
          }
          if ( out_data >= v57 )
            return 0;
          *out_data = v7 >> 24;
          v9 <<= 8;
          ++out_data;
          v7 <<= 8;
        }
      }
      v26 = *(_WORD *)(v14 + 10);
      if ( (_WORD)v26 )
      {
        if ( (_WORD)v26 < (_WORD)v23 )
          break;
      }
LABEL_39:
      v24 = v51;
      *(_WORD *)(v14 + 10) += 5;
      *(_WORD *)(v14 + 12) += 5;
LABEL_40:
      *(_WORD *)(v14 + 12) += 2;
      if ( v24 > 0xFBu || *(_WORD *)(v14 + 12) > 0xFF00u )
      {
        v27 = *(_WORD *)(v14 + 8);
        if ( (_WORD)v27 )
          v28 = (unsigned __int16)do_codeentry_stuff((struct_code_tables *)(v14 + 16 * v27));
        else
          v28 = 0;
        v29 = *(_WORD *)(v14 + 10);
        v29 = (_WORD)(v29 - (*(_WORD *)(v14 + 10) >> 1));
        *(_WORD *)(v14 + 10) = v29;
        v30 = v28 + v29;
        v24 = v51;
        *(_WORD *)(v14 + 12) = v30;
      }
      if ( v24 )
      {
LABEL_72:
        if ( v56 < 2 )
          ++v56;
        else
          v54 = *(_WORD *)(output_table2 + 14 + 16 * (unsigned __int16)v54);
        if ( (unsigned int)v47 >= 0xFFE )
        {
          v47 = 1;
          *(_DWORD *)output_table2 = 0;
          *(_DWORD *)(output_table2 + 4) = 0;
          *(_WORD *)(output_table2 + 14) = 0;
          *(_DWORD *)(output_table2 + 10) = 0x1010001u;
          *(_WORD *)(output_table2 + 8) = 0;
          v54 = 0;
          v56 = 0;
        }
        out_data3 = out_data;
        v10 = v61;
        goto LABEL_6;
      }
      v13 = v63;
      v14 = (intptr_t)(output_table2 + 16 * *(_WORD *)(v14 + 14));
      if ( v14 == output_table2 )
        goto LABEL_48;
    }
    v9 = v9 / v23 * v26;
    while ( 1 )
    {
      if ( (v7 ^ (v9 + v7)) >= 0x1000000 )
      {
        if ( v9 >= 0x10000 )
          goto LABEL_39;
        v9 = -v7 & 0xFFFF;
      }
      if ( out_data >= v57 )
        return 0;
      *out_data = v7 >> 24;
      v9 <<= 8;
      v7 <<= 8;
      ++out_data;
      v53 = v7;
    }
  }
  return 0;
}
